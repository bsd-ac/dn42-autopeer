from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    """
    Hello World!
    """
    return {"message": "Hello World!"}


@app.get("/autopeer")
async def autopeer(peer_asn: int):
    """
    Get peering information for given ASN.
    """
    return {"message": f"Autopeering with ASN {peer_asn}"}


@app.post("/autopeer")
async def autopeer(peer_asn: int):
    """
    Create or update a peering session with the given ASN.
    """
    return {"message": f"Autopeering with ASN {peer_asn}"}

@app.delete("/autopeer")
async def autopeer(peer_asn: int):
    """
    Delete peering session with the given ASN.
    """
    return {"message": f"Autopeering with ASN {peer_asn}"}
