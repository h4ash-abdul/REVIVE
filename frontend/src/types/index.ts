export interface DemoCase {
  scenario_key: string;
  title: string;
  mandate_id: string;
  amount: number;
  failure_code: string;
  initial_probability: number;
}

export interface TraceData {
  mandate_id: string;
  obligation_id: string;
  amount: number;
  currency: string;
  failure_category: string;
  failure_code: string;
  budget_remaining: number;
  obligation_status: string;
  strategy_result?: any;
  execution_record?: any;
  outcome?: any;
  audit_trail: AuditEvent[];
}

export interface AuditEvent {
  event_id: string;
  mandate_id: string;
  obligation_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  details: Record<string, any>;
}
