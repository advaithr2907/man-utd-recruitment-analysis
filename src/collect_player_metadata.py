from pathlib import Path
import pandas as pd
from ScraperFC.sofascore import API_PREFIX
from datetime import datetime, timezone, timedelta
from ScraperFC.utils import botasaurus_browser_get_json
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "2025-26"

MIN_MINUTES = 900

def load_candidate_ids():
    files = sorted(
        RAW_DATA_DIR.glob("sofascore__*__2025_2026.csv")
    )

    dfs = [
        pd.read_csv(file, usecols=["sofascore_id", "player", "minutes"])
        for file in files
    ]

    players = pd.concat(dfs, ignore_index=True)

    player_minutes = (
        players
        .groupby(["sofascore_id", "player"], as_index=False)
        .agg(season_minutes=("minutes", "sum"))
    )

    candidates = player_minutes[
        player_minutes["season_minutes"] >= MIN_MINUTES
    ].copy()

    return candidates

API_PREFIX = "https://api.sofascore.com/api/v1"


def fetch_player_metadata(player_id):
    url = f"{API_PREFIX}/player/{int(player_id)}"

    response = botasaurus_browser_get_json(url)
    
    if "player" not in response:
        error = response.get("error", {})
        code = error.get("code", "unknown")
        reason = error.get("reason", "unknown")

        raise RuntimeError(
            f"SofaScore request failed: {code} - {reason}"
        )

    player = response["player"]

    dob = None

    if "dateOfBirthTimestamp" in player:
        dob = (
            datetime.fromtimestamp(0, timezone.utc)
            + timedelta(seconds=player["dateOfBirthTimestamp"])
        ).date()

    return {
        "sofascore_id": player_id,
        "player": player.get("name"),
        "current_team": player.get("team", {}).get("name"),
        "position": player.get("position"),
        "positions_detailed": player.get("positionsDetailed"),
        "date_of_birth": dob,
        "height": player.get("height"),
        "weight": player.get("weight"),
        "preferred_foot": player.get("preferredFoot"),
        "country": player.get("country", {}).get("name"),
        "market_value": player.get(
            "proposedMarketValueRaw", {}
        ).get("value"),
        "market_value_currency": player.get(
            "proposedMarketValueRaw", {}
        ).get("currency"),
    }

if __name__ == "__main__":
    candidates = load_candidate_ids()

    output_file = RAW_DATA_DIR / "sofascore_player_metadata.csv"

    if output_file.exists():
        existing = pd.read_csv(output_file)

        completed_ids = set(
            existing["sofascore_id"].astype(int)
        )

        remaining = candidates[
            ~candidates["sofascore_id"]
            .astype(int)
            .isin(completed_ids)
        ].copy()

        metadata_rows = existing.to_dict("records")

    else:
        remaining = candidates.copy()
        metadata_rows = []

    print(f"Total eligible players: {len(candidates)}")
    print(f"Already collected: {len(metadata_rows)}")
    print(f"Remaining: {len(remaining)}")

    for attempt, (_, row) in enumerate(
        remaining.iterrows(),
        start=1
    ):
        player_id = row["sofascore_id"]
        player_name = row["player"]

        print(
            f"[{attempt}/{len(remaining)}] "
            f"Fetching {player_name}..."
        )

        try:
            metadata = fetch_player_metadata(player_id)
            metadata["season_minutes"] = row["season_minutes"]

            metadata_rows.append(metadata)

        except Exception as e:
            print(
                f"FAILED: {player_name} "
                f"({player_id}) — {e}"
            )

        if attempt % 25 == 0:
            pd.DataFrame(metadata_rows).to_csv(
                output_file,
                index=False
            )

        time.sleep(1)

    metadata_df = pd.DataFrame(metadata_rows)

    metadata_df.to_csv(
        output_file,
        index=False
    )

    print("\nCollection complete.")
    print(f"Successfully collected: {len(metadata_df)}")
    print(f"Saved to: {output_file}")

    