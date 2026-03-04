from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from kerykeion import AstrologicalSubject, NatalAspects, SynastryAspects
from kerykeion.charts import KerykeionChartSVG
import json
import os
from datetime import datetime

app = FastAPI(title="Astrology Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


class BirthData(BaseModel):
    name: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    city: str
    nation: str = "US"


class CompatibilityData(BaseModel):
    person1: BirthData
    person2: BirthData


PLANET_MEANINGS = {
    "Sun": "core identity, ego, life purpose",
    "Moon": "emotions, instincts, inner world",
    "Mercury": "communication, intellect, thought",
    "Venus": "love, beauty, values, pleasure",
    "Mars": "drive, passion, action, desire",
    "Jupiter": "expansion, luck, philosophy, growth",
    "Saturn": "discipline, karma, structure, lessons",
    "Uranus": "rebellion, innovation, sudden change",
    "Neptune": "dreams, spirituality, illusion",
    "Pluto": "transformation, power, rebirth",
}

SIGN_KEYWORDS = {
    "Ari": ("Aries", "♈", "bold, impulsive, pioneering"),
    "Tau": ("Taurus", "♉", "sensual, stubborn, grounded"),
    "Gem": ("Gemini", "♊", "curious, dual, communicative"),
    "Can": ("Cancer", "♋", "nurturing, sensitive, protective"),
    "Leo": ("Leo", "♌", "dramatic, generous, royal"),
    "Vir": ("Virgo", "♍", "analytical, precise, devoted"),
    "Lib": ("Libra", "♎", "balanced, charming, indecisive"),
    "Sco": ("Scorpio", "♏", "intense, secretive, transformative"),
    "Sag": ("Sagittarius", "♐", "adventurous, philosophical, free"),
    "Cap": ("Capricorn", "♑", "ambitious, patient, authoritative"),
    "Aqu": ("Aquarius", "♒", "rebellious, humanitarian, eccentric"),
    "Pis": ("Pisces", "♓", "dreamy, compassionate, mystical"),
}

HOROSCOPES = {
    "Aries": "The ram charges forward today. Mars fuels your ambition — act on instinct, but temper impulsiveness with awareness.",
    "Taurus": "Venus wraps you in earthly pleasures. Financial matters deserve attention. Trust your body's wisdom today.",
    "Gemini": "Mercury dances between ideas. Your words carry unusual power — use them wisely. A conversation shifts something.",
    "Cancer": "The Moon speaks to your depths. Emotional tides run high. Home and family offer comfort and clarity.",
    "Leo": "The Sun illuminates your natural throne. Your presence commands rooms without effort. Share your warmth generously.",
    "Virgo": "Details reveal hidden truths today. Your analytical mind cuts through illusion. Service to others brings unexpected reward.",
    "Libra": "Scales seek equilibrium. A choice you've avoided demands resolution. Beauty and harmony restore your sense of self.",
    "Scorpio": "Depths call to you. Transformation stirs beneath the surface. What you release today creates space for rebirth.",
    "Sagittarius": "The archer draws back for a long shot. Philosophy and adventure beckon. Truth arrives from an unexpected direction.",
    "Capricorn": "Saturn rewards patient effort. Your ambitions are well-founded — trust the slow climb. Authority recognizes your worth.",
    "Aquarius": "Uranus sparks unconventional solutions. Your vision is ahead of its time. Find others who can see what you see.",
    "Pisces": "Neptune dissolves boundaries between worlds. Intuition speaks louder than logic today. Dreams carry messages worth decoding.",
}


def get_sign_info(sign_code):
    return SIGN_KEYWORDS.get(sign_code, (sign_code, "?", "mysterious"))


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/chart")
async def get_chart(data: BirthData):
    try:
        subject = AstrologicalSubject(
            name=data.name,
            year=data.year,
            month=data.month,
            day=data.day,
            hour=data.hour,
            minute=data.minute,
            city=data.city,
            nation=data.nation,
            online=True,
        )

        planets = []
        planet_names = ["sun", "moon", "mercury", "venus", "mars",
                        "jupiter", "saturn", "uranus", "neptune", "pluto",
                        "mean_node", "chiron"]

        for p in planet_names:
            try:
                planet = getattr(subject, p)
                sign_data = SIGN_KEYWORDS.get(planet.sign[:3], (planet.sign, "?", ""))
                planets.append({
                    "name": planet.name,
                    "sign": sign_data[0],
                    "sign_symbol": sign_data[1],
                    "sign_keywords": sign_data[2],
                    "degree": round(planet.position, 2),
                    "house": planet.house_name,
                    "retrograde": planet.retrograde,
                    "meaning": PLANET_MEANINGS.get(planet.name, ""),
                })
            except Exception:
                continue

        # Big 3
        sun_sign = SIGN_KEYWORDS.get(subject.sun.sign[:3], (subject.sun.sign, "☀️", ""))[0]
        moon_sign = SIGN_KEYWORDS.get(subject.moon.sign[:3], (subject.moon.sign, "🌙", ""))[0]
        asc_sign = SIGN_KEYWORDS.get(subject.first_house.sign[:3], (subject.first_house.sign, "⬆️", ""))[0]

        return {
            "name": data.name,
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "ascendant": asc_sign,
            "planets": planets,
            "horoscope": HOROSCOPES.get(sun_sign, "The stars have a unique message for you today."),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/compatibility")
async def get_compatibility(data: CompatibilityData):
    try:
        p1 = data.person1
        p2 = data.person2

        subject1 = AstrologicalSubject(
            name=p1.name, year=p1.year, month=p1.month, day=p1.day,
            hour=p1.hour, minute=p1.minute, city=p1.city, nation=p1.nation, online=True,
        )
        subject2 = AstrologicalSubject(
            name=p2.name, year=p2.year, month=p2.month, day=p2.day,
            hour=p2.hour, minute=p2.minute, city=p2.city, nation=p2.nation, online=True,
        )

        synastry = SynastryAspects(subject1, subject2)
        aspects = synastry.get_relevant_aspects()

        harmonious = sum(1 for a in aspects if a["aspect"] in ["trine", "sextile", "conjunction"])
        tense = sum(1 for a in aspects if a["aspect"] in ["square", "opposition"])
        total = len(aspects) if aspects else 1

        score = min(100, max(0, int((harmonious / total) * 100 + 20)))

        sun1 = SIGN_KEYWORDS.get(subject1.sun.sign[:3], (subject1.sun.sign,))[0]
        sun2 = SIGN_KEYWORDS.get(subject2.sun.sign[:3], (subject2.sun.sign,))[0]

        return {
            "person1": p1.name,
            "person2": p2.name,
            "score": score,
            "harmonious_aspects": harmonious,
            "tense_aspects": tense,
            "total_aspects": len(aspects),
            "sun1": sun1,
            "sun2": sun2,
            "summary": get_compatibility_summary(score, p1.name, p2.name),
            "aspects": [
                {
                    "planet1": a["p1_name"],
                    "planet2": a["p2_name"],
                    "aspect": a["aspect"],
                    "orb": round(a["orbit"], 2),
                }
                for a in aspects[:10]
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_compatibility_summary(score, name1, name2):
    if score >= 80:
        return f"{name1} and {name2} share a rare cosmic alignment. Your souls recognize each other across lifetimes."
    elif score >= 60:
        return f"{name1} and {name2} complement each other beautifully. Growth and harmony intertwine in your connection."
    elif score >= 40:
        return f"{name1} and {name2} challenge and transform each other. Tension, when navigated consciously, forges depth."
    else:
        return f"{name1} and {name2} walk very different cosmic paths. Understanding requires patience and real effort."


@app.get("/api/horoscope/{sign}")
async def get_horoscope(sign: str):
    sign = sign.capitalize()
    if sign not in HOROSCOPES:
        raise HTTPException(status_code=404, detail="Sign not found")
    return {"sign": sign, "horoscope": HOROSCOPES[sign], "date": datetime.now().strftime("%B %d, %Y")}
