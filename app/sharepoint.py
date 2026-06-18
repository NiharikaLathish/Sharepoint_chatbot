"""Fetch a file live from SharePoint/OneDrive via Microsoft Graph.

Two ways to point it at a file (both work; the function handles either):

A) Graph endpoint + token (lasts ~1 hour, best for a session):
     SHAREPOINT_FILE_URL = https://graph.microsoft.com/v1.0/me/drive/root:/HR_Staff_Data.xlsx:/content
     GRAPH_TOKEN         = <access token from Graph Explorer>
   For a real SharePoint *site*, swap /me/drive for:
     /sites/{site-id}/drive/root:/Shared Documents/HR_Staff_Data.xlsx:/content

B) Pre-authenticated download URL (no token needed, but expires in minutes):
     In Graph Explorer run  GET /me/drive/root:/HR_Staff_Data.xlsx  and copy the
     "@microsoft.graph.downloadUrl" value into SHAREPOINT_FILE_URL. Leave GRAPH_TOKEN blank.

For production you'd replace the pasted token with an app registration (delegated
Files.Read.All) + sign-in, but the fetch code below stays the same.
"""
import httpx


def fetch_file_bytes(file_url: str, graph_token: str = "") -> bytes:
    if not file_url:
        raise RuntimeError("SHAREPOINT_FILE_URL is not set.")
    headers = {"Authorization": f"Bearer {graph_token}"} if graph_token else {}
    # follow_redirects lets the Graph /content endpoint redirect to the real
    # download host; httpx drops the auth header on that cross-host hop.
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(file_url, headers=headers)
    if resp.status_code == 401:
        raise RuntimeError(
            "Graph returned 401 — token missing/expired. Grab a fresh token from "
            "Graph Explorer, or use the @microsoft.graph.downloadUrl method instead."
        )
    if resp.status_code != 200:
        raise RuntimeError(f"SharePoint/Graph error {resp.status_code}: {resp.text[:200]}")
    return resp.content
