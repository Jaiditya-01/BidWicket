from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser
from app.models.match import Match, MatchStatus, Commentary
from app.models.notification import NotificationType
from app.models.team import Team
from app.schemas.match import MatchCreate, MatchUpdate, MatchOut, CommentaryCreate, AIGenerationRequest
from app.services.notification_service import notification_service
from app.websockets.connection_manager import match_manager
from starlette.concurrency import run_in_threadpool
from app.core.mailer import send_email
from app.core.config import settings

router = APIRouter(prefix="/matches", tags=["Matches"])


def _out(m: Match) -> MatchOut:
    return MatchOut(
        id=str(m.id),
        tournament_id=m.tournament_id,
        team1_id=m.team1_id,
        team2_id=m.team2_id,
        venue=m.venue,
        match_date=m.match_date,
        stage=m.stage,
        status=m.status,
        toss_winner_id=m.toss_winner_id,
        toss_decision=m.toss_decision,
        current_innings=m.current_innings,
        innings1=m.innings1,
        innings2=m.innings2,
        winner_id=m.winner_id,
        result_description=m.result_description,
        highlights_url=m.highlights_url,
        commentary=m.commentary,
        created_at=m.created_at,
    )


@router.post("/", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
async def create_match(body: MatchCreate, current_user: OrganizerUser):
    match = Match(**body.model_dump())
    await match.insert()
    return _out(match)


@router.get("/", response_model=List[MatchOut])
async def list_matches(
    current_user: CurrentUser,
    tournament_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    limit = max(1, min(100, limit))
    skip = (max(1, page) - 1) * limit
    query = Match.find(Match.tournament_id == tournament_id) if tournament_id else Match.find_all()
    matches = await query.skip(skip).limit(limit).to_list()
    return [_out(m) for m in matches]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: str, current_user: CurrentUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    return _out(m)


@router.patch("/{match_id}", response_model=MatchOut)
async def update_match(match_id: str, body: MatchUpdate, current_user: OrganizerUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    old_status = m.status
    old_winner_id = m.winner_id
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await m.set(update_data)

    m = await Match.get(match_id)
    if m:
        if old_status != m.status and m.status == MatchStatus.live:
            t1 = await Team.get(m.team1_id)
            t2 = await Team.get(m.team2_id)
            owner_ids = [t.owner_id for t in (t1, t2) if t]
            for owner_id in owner_ids:
                await notification_service.create(
                    user_id=owner_id,
                    notification_type=NotificationType.match_start,
                    title="Match started",
                    message="Your match is now live",
                    related_id=match_id,
                )
            # Email: match start
            if settings.SMTP_HOST:
                for owner_id in owner_ids:
                    from app.models.user import User
                    u = await User.get(owner_id)
                    if u:
                        try:
                            await run_in_threadpool(
                                send_email,
                                to_email=u.email,
                                subject="Your match is now LIVE — BidWicket",
                                html=f"<p>Hi {u.full_name},</p><p>Your match has started! Watch it live on BidWicket.</p>",
                            )
                        except Exception:
                            pass

        if (
            old_status != m.status
            and m.status == MatchStatus.completed
            and m.winner_id
            and m.winner_id != old_winner_id
        ):
            t1 = await Team.get(m.team1_id)
            t2 = await Team.get(m.team2_id)
            owner_ids = [t.owner_id for t in (t1, t2) if t]
            winner_team = await Team.get(m.winner_id)
            for owner_id in owner_ids:
                await notification_service.create(
                    user_id=owner_id,
                    notification_type=NotificationType.match_result,
                    title="Match result",
                    message=f"Winner: {winner_team.name if winner_team else m.winner_id}",
                    related_id=match_id,
                )
            # Email: match result
            if settings.SMTP_HOST:
                for owner_id in owner_ids:
                    from app.models.user import User
                    u = await User.get(owner_id)
                    if u:
                        try:
                            await run_in_threadpool(
                                send_email,
                                to_email=u.email,
                                subject="Match Result — BidWicket",
                                html=f"<p>Hi {u.full_name},</p><p>Match completed. Winner: <b>{winner_team.name if winner_team else 'N/A'}</b>.</p>",
                            )
                        except Exception:
                            pass

    await match_manager.broadcast(match_id, {"type": "score_update", "data": _out(m).model_dump()})
    return _out(m)


@router.post("/{match_id}/commentary", response_model=MatchOut)
async def add_commentary(match_id: str, body: CommentaryCreate, current_user: OrganizerUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")

    entry = Commentary(**body.model_dump())
    m.commentary.append(entry)

    # Determine which innings to update
    from app.models.match import InningsScore, BatterScore, BowlerScore
    
    if m.current_innings == 1:
        if m.innings1 is None:
            # Figure out who the default batting and bowling teams are.
            # If toss decision is bat, toss winner bats first.
            if m.toss_decision == "bat" and m.toss_winner_id == m.team1_id:
                batting_team = m.team1_id
                bowling_team = m.team2_id
            elif m.toss_decision == "bowl" and m.toss_winner_id == m.team1_id:
                batting_team = m.team2_id
                bowling_team = m.team1_id
            elif m.toss_decision == "bat" and m.toss_winner_id == m.team2_id:
                batting_team = m.team2_id
                bowling_team = m.team1_id
            elif m.toss_decision == "bowl" and m.toss_winner_id == m.team2_id:
                batting_team = m.team1_id
                bowling_team = m.team2_id
            else:
                # Fallback if toss isn't recorded
                batting_team = m.team1_id
                bowling_team = m.team2_id
                
            m.innings1 = InningsScore(batting_team_id=batting_team, bowling_team_id=bowling_team)
        else:
            if not m.innings1.batting_team_id and m.innings1.team_id:
                m.innings1.batting_team_id = m.innings1.team_id
                m.innings1.bowling_team_id = m.team2_id if m.innings1.team_id == m.team1_id else m.team1_id
        current_inning = m.innings1
    else:
        if m.innings2 is None:
            prev_batting = m.innings1.batting_team_id or m.innings1.team_id
            batting_team = m.team2_id if prev_batting == m.team1_id else m.team1_id
            bowling_team = prev_batting
            m.innings2 = InningsScore(batting_team_id=batting_team, bowling_team_id=bowling_team)
        current_inning = m.innings2

    # Update Team Score
    current_inning.runs += body.runs_scored
    if body.wicket:
        current_inning.wickets += 1
    current_inning.overs = body.over

    # Update Batter Stats
    if body.batter_id:
        batter = next((b for b in current_inning.batters if b.player_id == body.batter_id), None)
        if not batter:
            batter = BatterScore(player_id=body.batter_id)
            current_inning.batters.append(batter)
        
        batter.runs += body.runs_scored
        batter.balls_faced += 1
        if body.runs_scored == 4:
            batter.fours += 1
        elif body.runs_scored == 6:
            batter.sixes += 1
        if body.wicket:
            batter.is_out = True

    # Update Bowler Stats
    if body.bowler_id:
        bowler = next((b for b in current_inning.bowlers if b.player_id == body.bowler_id), None)
        if not bowler:
            bowler = BowlerScore(player_id=body.bowler_id)
            current_inning.bowlers.append(bowler)
        
        bowler.overs = body.over
        bowler.runs_conceded += body.runs_scored
        if body.wicket:
            bowler.wickets += 1

    # Auto-progression logic (All-out or Target Chased)
    old_status = m.status
    if m.status != MatchStatus.completed:
        team1x = await Team.get(m.team1_id)
        team2x = await Team.get(m.team2_id)
        team1_name = team1x.name if team1x else m.team1_id
        team2_name = team2x.name if team2x else m.team2_id

        bat1_name = team1_name if m.innings1.batting_team_id == m.team1_id else team2_name
        bat2_name = team2_name if m.innings1.batting_team_id == m.team1_id else team1_name

        if m.current_innings == 1:
            if m.innings1.wickets >= 10:
                m.current_innings = 2
        elif m.current_innings == 2:
            target = m.innings1.runs + 1
            if m.innings2.runs >= target:
                m.status = MatchStatus.completed
                m.winner_id = m.innings2.batting_team_id
                wickets_left = 10 - m.innings2.wickets
                m.result_description = f"{bat2_name} won by {wickets_left} wickets"
            elif m.innings2.wickets >= 10:
                m.status = MatchStatus.completed
                if m.innings2.runs < m.innings1.runs:
                    m.winner_id = m.innings1.batting_team_id
                    run_diff = m.innings1.runs - m.innings2.runs
                    m.result_description = f"{bat1_name} won by {run_diff} runs"
                else:
                    m.winner_id = None
                    m.result_description = "Match Tied"

    m.updated_at = datetime.now(timezone.utc)
    await m.save()

    # Trigger notifications if match automatically completed
    if old_status != MatchStatus.completed and m.status == MatchStatus.completed:
        t1 = await Team.get(m.team1_id)
        t2 = await Team.get(m.team2_id)
        owner_ids = [t.owner_id for t in (t1, t2) if t]
        if m.winner_id:
            winner_team = await Team.get(m.winner_id)
            win_msg = f"Winner: {winner_team.name if winner_team else m.winner_id}"
            win_html = f"<b>{winner_team.name if winner_team else 'N/A'}</b>"
        else:
            win_msg = "Match Tied"
            win_html = "<b>Match Tied</b>"

        for owner_id in owner_ids:
            await notification_service.create(
                user_id=owner_id,
                notification_type=NotificationType.match_result,
                title="Match result",
                message=win_msg,
                related_id=match_id,
            )
        if settings.SMTP_HOST:
            for owner_id in owner_ids:
                from app.models.user import User
                u = await User.get(owner_id)
                if u:
                    try:
                        await run_in_threadpool(
                            send_email,
                            to_email=u.email,
                            subject="Match Result — BidWicket",
                            html=f"<p>Hi {u.full_name},</p><p>Match completed! {win_html}.</p>",
                        )
                    except Exception:
                        pass

    # Broadcast commentary to all viewers
    payload = {"type": "commentary_update", "data": entry.model_dump()}
    await match_manager.broadcast(match_id, payload)

    # Broadcast updated scoreboard to all viewers
    await match_manager.broadcast(match_id, {"type": "score_update", "data": _out(m).model_dump()})

    # Emit dedicated wicket_update event
    if body.wicket:
        wicket_payload = {
            "type": "wicket_update",
            "data": {
                "match_id": match_id,
                "over": body.over,
                "description": body.ball_description,
            },
        }
        await match_manager.broadcast(match_id, wicket_payload)

    return _out(m)


@router.post("/{match_id}/generate-ai-commentary")
async def generate_ai_commentary(match_id: str, body: AIGenerationRequest, current_user: OrganizerUser):
    import random
    
    def generate_local_commentary(body):
        """Smart local commentary generator — no API needed, works instantly."""
        batter = body.batter_name
        bowler = body.bowler_name
        batting_team = body.batting_team or "the batting side"
        
        if body.is_wicket:
            templates = [
                f"OUT! {bowler} strikes! {batter} has to walk back to the pavilion. What a delivery!",
                f"WICKET! {bowler} has done it! {batter} is gone! The fielding side erupts in celebration!",
                f"Gone! {batter} couldn't handle that one from {bowler}. A crucial breakthrough!",
                f"That's the end of {batter}! {bowler} pumps the fist — what a moment in this match!",
                f"TIMBER! {bowler} sends {batter} packing! The crowd goes absolutely wild!",
                f"Edged and taken! {batter} departs as {bowler} picks up another scalp!",
            ]
        elif body.runs == 6:
            templates = [
                f"SIX! {batter} launches it into the stands! {bowler} can only watch it sail away!",
                f"MASSIVE! That's gone all the way! {batter} sends it into orbit against {bowler}!",
                f"Into the crowd! {batter} smashes {bowler} for a monster six! What a shot!",
                f"That's HUGE from {batter}! Picks up {bowler} and deposits it over the boundary!",
                f"Maximum! {batter} clears the ropes with absolute authority off {bowler}!",
            ]
        elif body.runs == 4:
            templates = [
                f"FOUR! {batter} finds the gap beautifully! {bowler} is under pressure now!",
                f"Cracking shot! {batter} drives {bowler} through the covers for a boundary!",
                f"That races away to the fence! {batter} is timing the ball superbly against {bowler}!",
                f"BOUNDARY! {batter} flicks it off the pads, no stopping that one from {bowler}!",
                f"Exquisite! {batter} punches {bowler} through the gap for four more!",
            ]
        elif body.runs == 0:
            templates = [
                f"Dot ball! {bowler} keeps it tight, {batter} defends solidly. Building pressure!",
                f"No run! {bowler} bowls a beauty, {batter} can't get it away. Terrific bowling!",
                f"Nothing doing! {bowler} is on the money, {batter} watchfully blocks it out.",
                f"Tight from {bowler}! {batter} respects the good length. That's disciplined cricket.",
                f"Beaten! {bowler} gets one past the outside edge of {batter}! What a delivery!",
            ]
        elif body.runs == 1:
            templates = [
                f"Single taken! {batter} nudges {bowler} into the gap and rotates the strike.",
                f"Smart cricket from {batter}, works it off {bowler} for a quick single.",
                f"{batter} dabs it to the off side for one. Keeping the scoreboard ticking against {bowler}.",
                f"Just the one. {batter} pushes {bowler} gently and scampers through for a single.",
            ]
        elif body.runs == 2:
            templates = [
                f"Two runs! {batter} punches {bowler} into the gap and comes back for the second!",
                f"Good running! {batter} finds the gap off {bowler} and they pick up a couple.",
                f"Well played! {batter} places it neatly and the batters run hard for two.",
            ]
        elif body.runs == 3:
            templates = [
                f"Three runs! {batter} drives it deep and they run hard! Excellent placement against {bowler}!",
                f"Superb running between the wickets! {batter} gets three off {bowler}.",
            ]
        else:
            templates = [
                f"{batter} scores {body.runs} off {bowler}! Great batting from {batting_team}!",
                f"{body.runs} runs! {batter} is looking dangerous out there against {bowler}!",
            ]
        
        return random.choice(templates)
    
    try:
        english_text = None
        
        # Try Gemini first (optional enhancement)
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                prompt = (
                    f"You are a passionate cricket commentator. Generate exactly 1 or 2 short, thrilling sentences of live commentary for this ball.\n"
                    f"Context: {body.batting_team} is batting, {body.bowling_team} is bowling.\n"
                    f"Over: {body.over}, Bowler: {body.bowler_name}, Batter: {body.batter_name}\n"
                    f"Runs: {body.runs}, Wicket: {'Yes' if body.is_wicket else 'No'}\n"
                    f"Only return the commentary string, nothing else."
                )
                
                model = genai.GenerativeModel('gemini-2.0-flash-lite')
                response = model.generate_content(prompt)
                english_text = response.text.strip()
            except Exception:
                pass  # Silently fall back to local generator
        
        # Fallback to local smart generator if Gemini failed or quota exceeded
        if not english_text:
            english_text = generate_local_commentary(body)
        
        # Free translation — no API key, no quota, works forever
        from deep_translator import GoogleTranslator
        hindi_text = GoogleTranslator(source='en', target='hi').translate(english_text)
        
        return {
            "commentary": english_text,
            "hindi_commentary": hindi_text,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(match_id: str, current_user: OrganizerUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    await m.delete()


# ── WebSocket: live match updates ─────────────────────────────────────────────
@router.websocket("/{match_id}/ws")
async def match_websocket(websocket: WebSocket, match_id: str):
    await match_manager.connect(match_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive ping
    except WebSocketDisconnect:
        match_manager.disconnect(match_id, websocket)
