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

export type TournamentType = 'league' | 'knockout' | 't20' | 'odi' | 'test';
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
  tournament_id?: string;
  budget: number;
  remaining_budget: number;
  logo_url?: string;
  home_ground?: string;
  players: string[];
  created_at: string;
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

export interface InningsScore {
  team_id: string;
  runs: number;
  wickets: number;
  overs: number;
  extras: number;
}

export interface Commentary {
  over: number;
  ball_description: string;
  runs_scored: number;
  wicket: boolean;
  timestamp: string;
}

export interface Match {
  id: string;
  tournament_id: string;
  team1_id: string;
  team2_id: string;
  venue?: string;
  match_date?: string;
  status: MatchStatus;
  toss_winner_id?: string;
  toss_decision?: string;
  innings1?: InningsScore;
  innings2?: InningsScore;
  winner_id?: string;
  result_description?: string;
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
  sold_at?: string;
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
  | { type: 'item_sold'; data: { auction_item_id: string; player_id: string; sold_price: number; winning_team_id: string } }
  | { type: 'item_unsold'; data: { auction_item_id: string } }
  | { type: 'item_activated'; item_id: string; base_price: number; player_id: string }
  | { type: 'auction_status'; status: AuctionStatus }
  | { type: 'score_update'; data: Match }
  | { type: 'commentary'; data: Commentary };
