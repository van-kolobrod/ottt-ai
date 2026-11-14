"""ОТТТ-ИИ: minimal append-only event memory with temporal/semantic indexes.

Python >=3.10; standard library only. Example: python ottt_memory.py demo
"""
import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Memory:
    def __init__(self, path='ottt_memory.sqlite3'):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                occurred_at TEXT,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                source TEXT,
                parent_id TEXT REFERENCES events(id)
            );
            CREATE INDEX IF NOT EXISTS idx_event_time ON events(recorded_at);
            CREATE INDEX IF NOT EXISTS idx_occurred_time ON events(occurred_at);
            CREATE TABLE IF NOT EXISTS concepts (
                name TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS event_concepts (
                event_id TEXT NOT NULL REFERENCES events(id),
                concept TEXT NOT NULL REFERENCES concepts(name),
                PRIMARY KEY(event_id, concept)
            );
            CREATE INDEX IF NOT EXISTS idx_semantic ON event_concepts(concept, event_id);
            CREATE TABLE IF NOT EXISTS event_links (
                source_id TEXT NOT NULL REFERENCES events(id),
                relation TEXT NOT NULL,
                target_id TEXT NOT NULL REFERENCES events(id),
                PRIMARY KEY(source_id, relation, target_id)
            );
            CREATE TABLE IF NOT EXISTS access_tier (
                event_id TEXT PRIMARY KEY REFERENCES events(id),
                tier TEXT NOT NULL CHECK(tier IN ('active','consolidated','archive')),
                summary TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_state (
                event_id TEXT PRIMARY KEY REFERENCES events(id),
                last_reviewed_at TEXT,
                review_count INTEGER NOT NULL DEFAULT 0
            );
        ''')
        self.db.commit()

    def add(self, kind, payload, concepts=(), occurred_at=None, source=None, parent_id=None,
            links=()):
        event_id = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',
                            (event_id, now(), occurred_at, kind,
                             json.dumps(payload, ensure_ascii=False, sort_keys=True), source, parent_id))
            self.db.execute('INSERT INTO access_tier VALUES (?,?,?,?)',
                            (event_id, 'active', None, now()))
            self._tag(event_id, concepts)
            self.db.executemany('INSERT INTO event_links VALUES (?,?,?)',
                                [(event_id, relation, target) for relation, target in links])
        return event_id

    def tag(self, event_id, concepts):
        # Index changes are not edits to the original event.
        with self.db:
            self._tag(event_id, concepts)

    def _tag(self, event_id, concepts):
        for concept in concepts:
            self.db.execute('INSERT OR IGNORE INTO concepts VALUES (?)', (concept,))
            self.db.execute('INSERT OR IGNORE INTO event_concepts VALUES (?,?)', (event_id, concept))

    def link(self, source_id, relation, target_id):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO event_links VALUES (?,?,?)',
                            (source_id, relation, target_id))

    def get(self, event_id):
        row = self.db.execute('''SELECT e.*, a.tier, a.summary FROM events e
                                 JOIN access_tier a ON a.event_id=e.id WHERE e.id=?''',
                              (event_id,)).fetchone()
        if row is None:
            raise KeyError(event_id)
        result = dict(row)
        result['payload'] = json.loads(result['payload'])
        result['concepts'] = [r[0] for r in self.db.execute(
            'SELECT concept FROM event_concepts WHERE event_id=? ORDER BY concept', (event_id,))]
        return result

    def search(self, concept=None, include_archive=False, limit=100):
        sql = '''SELECT e.id FROM events e JOIN access_tier a ON a.event_id=e.id'''
        args = []
        if concept:
            sql += ' JOIN event_concepts ec ON ec.event_id=e.id'
        where = []
        if concept:
            where.append('ec.concept=?')
            args.append(concept)
        if not include_archive:
            where.append("a.tier!='archive'")
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY e.recorded_at DESC, e.id DESC LIMIT ?'
        args.append(limit)
        return [self.get(r[0]) for r in self.db.execute(sql, args)]

    def consolidate(self, event_id, summary):
        if not summary.strip():
            raise ValueError('Summary must not be empty')
        with self.db:
            self.db.execute('UPDATE access_tier SET tier=?,summary=?,updated_at=? WHERE event_id=?',
                            ('consolidated', summary, now(), event_id))
        return self.get(event_id)

    def archive(self, event_id):
        # No deletion, no loss of raw payload. Summary can be kept as a retrieval hint.
        with self.db:
            self.db.execute('UPDATE access_tier SET tier=?,updated_at=? WHERE event_id=?',
                            ('archive', now(), event_id))
        return self.get(event_id)

    def reactivate(self, event_id):
        with self.db:
            self.db.execute('UPDATE access_tier SET tier=?,updated_at=? WHERE event_id=?',
                            ('active', now(), event_id))
        return self.get(event_id)

    def audit(self, limit=50):
        """Conservative audit: report candidates; never auto-delete or auto-infer facts."""
        rows = self.db.execute('''SELECT e.id FROM events e
            LEFT JOIN audit_state s ON s.event_id=e.id
            ORDER BY COALESCE(s.review_count,0), e.recorded_at LIMIT ?''', (limit,)).fetchall()
        result = []
        with self.db:
            for row in rows:
                eid = row[0]
                e = self.get(eid)
                links = self.db.execute('''SELECT relation,target_id FROM event_links
                                            WHERE source_id=?''', (eid,)).fetchall()
                result.append({'id': eid, 'kind': e['kind'], 'tier': e['tier'],
                               'concepts': e['concepts'], 'outgoing_links': len(links),
                               'needs_classification': not bool(e['concepts'])})
                self.db.execute('''INSERT INTO audit_state(event_id,last_reviewed_at,review_count)
                    VALUES(?,?,1) ON CONFLICT(event_id) DO UPDATE SET
                    last_reviewed_at=excluded.last_reviewed_at,
                    review_count=review_count+1''', (eid, now()))
        return result

    def close(self):
        self.db.close()


def demo(path):
    m = Memory(path)
    observation = m.add('observation', {'description': 'На столе три книги',
                                       'positions': {'red': 'left', 'blue': 'middle', 'green': 'right'}},
                        concepts=['предмет', 'книга', 'стол'], source='demo')
    interpretation = m.add('interpretation', {'statement': 'Наблюдалась группа из трёх книг',
                                             'confidence': 0.9},
                           concepts=['группа', 'книга'], parent_id=observation)
    m.link(interpretation, 'interprets', observation)
    m.consolidate(observation, 'На столе лежали три книги')
    m.archive(observation)
    print('Active search:', [e['id'] for e in m.search('книга')])
    print('Archive search:', [e['id'] for e in m.search('книга', include_archive=True)])
    print('Original after archive:', json.dumps(m.get(observation)['payload'], ensure_ascii=False))
    print('Audit:', json.dumps(m.audit(), ensure_ascii=False))
    m.reactivate(observation)
    assert m.get(observation)['tier'] == 'active'
    m.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['demo', 'audit'])
    parser.add_argument('--db', default='ottt_memory.sqlite3')
    args = parser.parse_args()
    if args.command == 'demo':
        demo(args.db)
    else:
        memory = Memory(args.db)
        print(json.dumps(memory.audit(), ensure_ascii=False, indent=2))
        memory.close()
