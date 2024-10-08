m_001 = [
    """
CREATE TABLE peerinfo (
	"ASN" INTEGER NOT NULL, 
	"DESCRIPTION" VARCHAR(30) NOT NULL, 
	"PEER_IP" VARCHAR NOT NULL, 
	"PEER_PORT" INTEGER NOT NULL, 
	"PEER_PUBKEY" VARCHAR(60) NOT NULL, 
	"PEER_PSK" VARCHAR(60) NOT NULL, 
	"LL_IP4" VARCHAR NOT NULL, 
	"LL_IP6" VARCHAR NOT NULL, 
	"DN42_IP4" VARCHAR NOT NULL, 
	"DN42_IP6" VARCHAR NOT NULL, 
	PRIMARY KEY ("ASN"), 
	UNIQUE ("PEER_IP"), 
	UNIQUE ("PEER_PORT"), 
	UNIQUE ("PEER_PUBKEY"), 
	UNIQUE ("PEER_PSK"), 
	UNIQUE ("LL_IP4"), 
	UNIQUE ("LL_IP6"), 
	UNIQUE ("DN42_IP4"), 
	UNIQUE ("DN42_IP6")
);
""",
    "CREATE INDEX IF NOT EXISTS idx_ASN ON peerinfo (ASN);",
    "CREATE INDEX IF NOT EXISTS idx_DESCRIPTION ON peerinfo (DESCRIPTION);",
    "CREATE INDEX IF NOT EXISTS idx_PEER_IP ON peerinfo (PEER_IP);",
    "CREATE INDEX IF NOT EXISTS idx_PEER_PORT ON peerinfo (PEER_PORT);",
    "CREATE INDEX IF NOT EXISTS idx_PEER_PUBKEY ON peerinfo (PEER_PUBKEY);",
    "CREATE INDEX IF NOT EXISTS idx_PEER_PSK ON peerinfo (PEER_PSK);",
    "CREATE INDEX IF NOT EXISTS idx_LL_IP4 ON peerinfo (LL_IP4);",
    "CREATE INDEX IF NOT EXISTS idx_LL_IP6 ON peerinfo (LL_IP6);",
    "CREATE INDEX IF NOT EXISTS idx_DN42_IP4 ON peerinfo (DN42_IP4);",
    "CREATE INDEX IF NOT EXISTS idx_DN42_IP6 ON peerinfo (DN42_IP6);",
]

migrations = [
    m_001,
]
