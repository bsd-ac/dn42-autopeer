m_001 = """
CREATE TABLE IF NOT EXISTS peers (
    ASN INT PRIMARY KEY NOT NULL,
    WG_PORT INT NOT NULL UNIQUE,
    WG_PRIVKEY TEXT NOT NULL UNIQUE,
    WG_PSK TEXT NOT NULL UNIQUE,
    WG_LL6 TEXT NOT NULL UNIQUE
    );

CREATE INDEX IF NOT EXISTS idx_wg_port ON peers (WG_PORT);
CREATE INDEX IF NOT EXISTS idx_wg_privkey ON peers (WG_PRIVKEY);
CREATE INDEX IF NOT EXISTS idx_wg_psk ON peers (WG_PSK);
CREATE INDEX IF NOT EXISTS idx_wg_ll6 ON peers (WG_LL6);
"""

migrations = [
    m_001,
]
