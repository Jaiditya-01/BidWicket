// Shared TypeScript interfaces mirroring backend schemas

export interface User {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type TournamentType = 'league' | 'knockout' | 'hybrid' | 't20' | 'odi' | 'test';
export type TournamentStatus = 'upcoming' | 'ongoing' | 'completed' | 'cancelled';

export interface Tournament {
  id: string;
  name: string;
  description?: string;
  tournament_type: TournamentType;
  status: TournamentStatus;
  start_date?: string;
  end_date?: string;
  organizer_id?: string;
  max_teams: number;
  logo_url?: string;
  created_at: string;
}

export interface Team {
  id: string;
  name: string;
  short_name?: string;
  owner_id: string;
  owner_name?: string;
  tournament_id?: string;
  budget: number;
  remaining_budget: number;
  logo_url?: string;
  home_ground?: string;
  players: string[];
  created_at: string;
}

export interface TeamHistoryOut {
  team_id: string;
  played: number;
  won: number;
  lost: number;
  tied: number;
}

export type PlayerRole = 'batsman' | 'bowler' | 'all_rounder' | 'wicket_keeper';
export type BattingStyle = 'right_hand' | 'left_hand';
export type BowlingStyle =
  | 'right_arm_fast' | 'right_arm_medium' | 'left_arm_fast'
  | 'left_arm_medium' | 'right_arm_spin' | 'left_arm_spin' | 'none';

export interface PlayerStats {
  matches: number;
  runs: number;
  wickets: number;
  average: number;
  strike_rate: number;
  economy_rate: number;
  centuries: number;
  half_centuries: number;
  five_wicket_hauls: number;
}

export interface PlayerStatsOut extends PlayerStats {
  player_id: string;
  name: string;
}

export interface Player {
  id: string;
  name: string;
  country: string;
  age?: number;
  role: PlayerRole;
  batting_style: BattingStyle;
  bowling_style: BowlingStyle;
  bio?: string;
  photo_url?: string;
  base_price: number;
  stats: PlayerStats;
  team_id?: string;
  is_available: boolean;
  created_at: string;
}

export type MatchStatus = 'scheduled' | 'live' | 'completed' | 'abandoned';
export type MatchStage = 'league' | 'quarter_final' | 'semi_final' | 'final';

export interface BatterScore {
  player_id: string;
  runs: number;
  balls_faced: number;
  fours: number;
  sixes: number;
  is_out: boolean;
}

export interface BowlerScore {
  player_id: string;
  overs: number;
  runs_conceded: number;
  wickets: number;
  maidens: number;
}

export interface InningsScore {
  batting_team_id: string;
  bowling_team_id?: string;
  team_id?: string;
  runs: number;
  wickets: number;
  overs: number;
  extras: number;
  batters: BatterScore[];
  bowlers: BowlerScore[];
}

export interface Commentary {
  over: number;
  ball_description: string;
  runs_scored: number;
  wicket: boolean;
  batter_id?: string;
  bowler_id?: string;
  timestamp: string;
}

export interface Match {
  id: string;
  tournament_id: string;
  team1_id: string;
  team2_id: string;
  venue?: string;
  match_date?: string;
  stage: string;
  status: string;
  toss_winner_id?: string;
  toss_decision?: string;
  current_innings: number;
  innings1?: InningsScore;
  innings2?: InningsScore;
  winner_id?: string;
  result_description?: string;
  highlights_url?: string;
  commentary: Commentary[];
  created_at: string;
}

export type AuctionStatus = 'upcoming' | 'live' | 'paused' | 'completed';
export type AuctionItemStatus = 'pending' | 'active' | 'sold' | 'unsold';

export interface Auction {
  id: string;
  tournament_id: string;
  name: string;
  status: AuctionStatus;
  bid_timer_seconds: number;
  current_item_id?: string;
  scheduled_at?: string;
  started_at?: string;
  ended_at?: string;
  created_at: string;
}

export interface AuctionItem {
  id: string;
  auction_id: string;
  player_id: string;
  base_price: number;
  current_bid: number;
  highest_bidder_id?: string;
  winning_team_id?: string;
  status: AuctionItemStatus;
  bid_count: number;
  activated_at?: string;
  ends_at?: string;
  sold_at?: string;
  finalized_at?: string;
}

export type NotificationType =
  | 'auction_start'
  | 'bid_placed'
  | 'player_sold'
  | 'outbid'
  | 'match_start'
  | 'match_result'
  | 'system';

export interface Notification {
  id: string;
  user_id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  is_read: boolean;
  related_id?: string;
  created_at: string;
}

export interface SearchResult {
  entity: string;
  id: string;
  title: string;
  subtitle?: string;
}

export interface AdminOverview {
  users: number;
  tournaments: number;
  teams: number;
  players: number;
  matches: number;
  auctions: number;
  auction_items: number;
  bids: number;
}

export interface Bid {
  id: string;
  auction_item_id: string;
  auction_id: string;
  user_id: string;
  team_id: string;
  amount: number;
  is_winning: boolean;
  timestamp: string;
}

// WebSocket event shapes
export type WsEvent =
  | { type: 'new_bid'; data: { auction_item_id: string; amount: number; bidder_id: string; team_id: string; bid_count: number } }
  | { type: 'timer_tick'; data: { auction_item_id: string; remaining_seconds: number; ends_at: string } }
  | { type: 'item_sold'; data: { auction_item_id: string; player_id: string; sold_price: number; winning_team_id: string; reason?: string } }
  | { type: 'item_unsold'; data: { auction_item_id: string; reason?: string } }
  | { type: 'item_activated'; item_id: string; base_price: number; player_id: string }
  | { type: 'auction_status'; status: AuctionStatus }
  | { type: 'auction_finalized'; auction_id: string }
  | { type: 'state_update'; data: { auction_item_id: string; status: 'sold' | 'unsold' } }
  | { type: 'score_update'; data: Match }
  | { type: 'commentary_update'; data: Commentary }
  | { type: 'wicket_update'; data: { match_id: string; over: number; description: string } };
