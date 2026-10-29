"""Idempotent import of previously completed M1-1 KPX solar dataset."""
import csv
import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from app.store import get_store

load_dotenv()


def get_csv_path():
    path = os.environ.get("SOLAR_CSV_PATH")
    if path:
        return Path(path)
    here = Path(__file__).resolve()
    possibilities = [
        here.parents[1] / "data" / "daily_solar.csv",  # M1-2 repository root
        here.parents[2] / "data" / "daily_solar.csv",  # if nested within another project
    ]
    for p in possibilities:
        if p.exists():
            return p
    raise FileNotFoundError("첫 과제의 data/daily_solar.csv를 찾지 못했습니다. SOLAR_CSV_PATH를 설정하세요.")


def read_rows(path):
    result = []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"date", "energy_mwh"}.issubset(set(reader.fieldnames or [])):
            raise ValueError("CSV에 date 및 energy_mwh 컬럼이 필요합니다.")
        for row in reader:
            day = date.fromisoformat(row["date"]).isoformat()
            amount = float(row["energy_mwh"])
            if amount < 0 or not __import__("math").isfinite(amount):
                raise ValueError(f"발전량이 유효하지 않습니다: {day}")
            result.append({"id": day, "date": day, "value": amount,
                           "memo": "KPX 2025년 일별 태양광 거래량", "source": "KPX / M1-1"})
    if len(result) < 100 or len({x["date"] for x in result}) != len(result):
        raise ValueError("관측값 100개 미만이거나 날짜가 중복됩니다.")
    return sorted(result, key=lambda r: r["date"])


def main():
    path = get_csv_path()
    records = read_rows(path)
    inserted = get_store().seed_rows(records)
    print(f"입력 {len(records)}개 / 신규 등록 {inserted}개 / 기존 데이터 유지: {path}")


if __name__ == "__main__":
    main()
