-- Track which responders are assigned to which cases
CREATE TABLE IF NOT EXISTS responder_assignment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES "case"(id) ON DELETE CASCADE,
    responder_id UUID REFERENCES "user"(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'notified', -- notified, confirmed, en_route, arrived, completed
    notified_at TIMESTAMPTZ DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    arrived_at TIMESTAMPTZ,
    distance_km DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(case_id, responder_id)
);

-- Create indexes for queries
CREATE INDEX IF NOT EXISTS idx_responder_assignment_case ON responder_assignment(case_id);
CREATE INDEX IF NOT EXISTS idx_responder_assignment_responder ON responder_assignment(responder_id);
CREATE INDEX IF NOT EXISTS idx_responder_assignment_status ON responder_assignment(status);

-- Add comments
COMMENT ON TABLE responder_assignment IS 'Tracks which responders are assigned to emergency cases';
COMMENT ON COLUMN responder_assignment.status IS 'notified = SMS sent, confirmed = replied YES, en_route = on the way, arrived = at scene';
COMMENT ON COLUMN responder_assignment.distance_km IS 'Distance from responder to emergency at time of notification';