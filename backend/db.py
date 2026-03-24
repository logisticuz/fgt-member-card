"""
Database layer for membership card system.
Reads from the shared Postgres (players table, card_ids table).
Uses psycopg3 with connection pool — same pattern as fgt-checkin-system.
"""

import os
import logging
import uuid as uuid_lib

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.critical("Missing DATABASE_URL in .env")
    raise EnvironmentError("Missing DATABASE_URL in .env")

_pool = None


def _get_pool():
    """Lazy-init a connection pool."""
    global _pool
    if _pool is None:
        import psycopg_pool  # type: ignore

        _pool = psycopg_pool.ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"autocommit": True},
        )
        logger.info("Postgres connection pool initialized (member-card)")
    return _pool


def _generate_card_id() -> str:
    """Generate a short unique card ID like FGC-A7K9X2."""
    import random
    import string

    chars = string.ascii_uppercase + string.digits
    # Remove ambiguous characters (0/O, 1/I/L)
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "").replace("L", "")
    code = "".join(random.choices(chars, k=6))
    return f"FGC-{code}"


# --- Card operations ---

def get_card(card_id: str) -> dict | None:
    """Look up card_id → player data."""
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.card_id, p.uuid, p.name, p.tag,
                       p.total_events, p.favorite_game,
                       p.first_seen, p.last_seen
                FROM card_ids c
                JOIN players p ON p.uuid = c.player_uuid
                WHERE c.card_id = %s
                """,
                (card_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "card_id": row[0],
        "uuid": row[1],
        "name": row[2],
        "tag": row[3],
        "total_events": row[4],
        "favorite_game": row[5],
        "first_seen": row[6].isoformat() if row[6] else None,
        "last_seen": row[7].isoformat() if row[7] else None,
    }


def get_card_id_for_player(player_uuid: str) -> str | None:
    """Check if player already has a card."""
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT card_id FROM card_ids WHERE player_uuid = %s",
                (player_uuid,),
            )
            row = cur.fetchone()
    return row[0] if row else None


def create_card_id(player_uuid: str) -> str:
    """Generate and store a new card ID for a player."""
    card_id = _generate_card_id()

    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            # Retry if card_id collision (extremely unlikely)
            for _ in range(5):
                try:
                    cur.execute(
                        "INSERT INTO card_ids (card_id, player_uuid) VALUES (%s, %s)",
                        (card_id, player_uuid),
                    )
                    logger.info(f"Card created: {card_id} -> {player_uuid}")
                    return card_id
                except Exception:
                    card_id = _generate_card_id()

    raise RuntimeError("Failed to generate unique card ID")


# --- Player operations ---

def find_player_by_tag(tag: str) -> dict | None:
    """Find a player by tag (case-insensitive). Falls back to name search."""
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            # Try tag first (most reliable match)
            cur.execute(
                """
                SELECT uuid, name, tag
                FROM players
                WHERE LOWER(tag) = LOWER(%s)
                LIMIT 1
                """,
                (tag.strip(),),
            )
            row = cur.fetchone()

            # Fallback: try name match
            if not row:
                cur.execute(
                    """
                    SELECT uuid, name, tag
                    FROM players
                    WHERE LOWER(name) = LOWER(%s)
                    LIMIT 1
                    """,
                    (tag.strip(),),
                )
                row = cur.fetchone()

    if not row:
        return None

    return {"uuid": row[0], "name": row[1], "tag": row[2]}


def create_player(name: str, tag: str | None = None) -> str:
    """Create a minimal player entry. Returns the new UUID."""
    player_uuid = str(uuid_lib.uuid4())

    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO players (uuid, name, tag, total_events, first_seen, last_seen)
                VALUES (%s, %s, %s, 0, NOW(), NOW())
                """,
                (player_uuid, name, tag),
            )

    logger.info(f"Player created: {player_uuid} ({name})")
    return player_uuid


def update_player_membership(player_uuid: str, is_member: bool) -> None:
    """Update the is_member flag on a player. Safe if column doesn't exist."""
    try:
        with _get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE players SET is_member = %s WHERE uuid = %s",
                    (is_member, player_uuid),
                )
    except Exception as e:
        logger.warning(f"Could not update is_member (column may not exist): {e}")
