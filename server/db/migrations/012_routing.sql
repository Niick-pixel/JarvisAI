-- Smart model routing (server/chat/routing.py): the one sentence saying why a model answered,
-- kept on the answer so the reason survives a reload and stays next to what it explains.
ALTER TABLE messages ADD COLUMN route_note TEXT;
