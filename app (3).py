import math, json, datetime as dt
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime
from html import escape
import requests, pandas as pd, streamlit as st
import streamlit.components.v1 as components

TZ = ZoneInfo("Europe/Paris")
now = lambda: dt.datetime.now(TZ)

st.set_page_config(page_title="Hub Perso", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
PAL = {
    "🔵 Bleu néon": {"A": "#00b4ff", "B": "#0b6fb8", "BG": "#041a33", "PANEL": "#06142a", "TXT": "#9fdcff"},
    "🔴 Rouge & or": {"A": "#ffc933", "B": "#c62828", "BG": "#2a0607", "PANEL": "#1a0506", "TXT": "#ffe8a3"},
}


def css():
    p = PAL.get(st.session_state.get("theme"), PAL["🔵 Bleu néon"])
    c = """<style>
:root{--primary-color:__A__}
.stApp{background:radial-gradient(circle at 20% 0%,__BG__ 0%,#000 55%)}
[data-testid=stHeader]{background:transparent}
#MainMenu,footer{visibility:hidden}
.block-container{padding:1rem .7rem 4rem!important;max-width:1200px}
h1,h2,h3{color:__A__!important;text-shadow:0 0 12px __A__88;letter-spacing:.5px}
input[type=checkbox],input[type=radio]{accent-color:__A__}
span[data-baseweb=tag]{background:__B__!important;color:#fff!important}
.stTabs [data-baseweb=tab-list]{overflow-x:auto;flex-wrap:nowrap;gap:4px;scrollbar-width:none}
.stTabs [data-baseweb=tab]{flex:0 0 auto;white-space:nowrap;background:__PANEL__;border:1px solid __B__;border-radius:10px 10px 0 0;padding:8px 14px;color:__TXT__}
.stTabs [aria-selected=true]{background:__B__55;border-color:__A__;box-shadow:0 0 12px __A__66;color:#fff}
.stTabs [data-baseweb=tab-highlight]{background:__A__!important}
.stButton>button,.stDownloadButton>button{border:1px solid __A__;background:__PANEL__;color:__A__;border-radius:8px;min-height:44px}
.stButton>button:hover,.stDownloadButton>button:hover{background:__A__;color:#000;box-shadow:0 0 14px __A__}
.card{background:__PANEL__;border:1px solid __B__;border-left:4px solid __A__;border-radius:12px;padding:10px 12px;margin:8px 0}
.card a:hover{color:__A__!important}
.muted{color:__TXT__;font-size:.8rem;opacity:.85}
.bar{height:8px;border-radius:6px;background:#ffffff18}
.bar>div{height:100%;border-radius:6px;background:linear-gradient(90deg,__B__,__A__)}
@media(max-width:640px){
h1{font-size:1.5rem!important}h2,h3{font-size:1.15rem!important}
.stButton>button,.stDownloadButton>button{width:100%;min-height:48px}
[data-testid=stMetricValue]{font-size:1.4rem}
.stTabs [data-baseweb=tab]{padding:6px 10px;font-size:.85rem}
}
</style>"""
    for k, v in p.items():
        c = c.replace("__" + k + "__", v)
    st.markdown(c, unsafe_allow_html=True)


css()


def secret(k):
    try:
        return st.secrets.get(k, "")
    except Exception:
        return ""


@st.cache_data(ttl=600, show_spinner=False)
def fetch(url, params=None, headers=None, raw=False):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        return r.text if raw else r.json()
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _fr(text):  # une exception n'est jamais mise en cache
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    try:
        parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        return "\n".join(GoogleTranslator(source="en", target="fr").translate(p) or "" for p in parts)
    except Exception:
        parts = [text[i:i + 450] for i in range(0, len(text), 450)]
        return "".join(MyMemoryTranslator(source="en-GB", target="fr-FR").translate(p) or "" for p in parts)


def fr(text):
    if st.session_state.get("lang", "Français") != "Français":
        return text
    try:
        return _fr(text)
    except Exception:
        st.toast("Traduction indisponible : texte affiché en anglais")
        return text


# ───────────────────────── RECETTES ─────────────────────────
ING = {"Poulet": "chicken", "Bœuf": "beef", "Porc": "pork", "Agneau": "lamb", "Saumon": "salmon", "Thon": "tuna",
       "Crevettes": "prawns", "Œufs": "eggs", "Lait": "milk", "Beurre": "butter", "Crème": "double cream",
       "Fromage": "cheese", "Parmesan": "parmesan", "Mozzarella": "mozzarella", "Riz": "rice", "Pâtes": "pasta",
       "Spaghetti": "spaghetti", "Pommes de terre": "potatoes", "Farine": "flour", "Sucre": "sugar",
       "Tomates": "tomatoes", "Oignon": "onion", "Ail": "garlic", "Carottes": "carrots", "Champignons": "mushrooms",
       "Poivron": "red pepper", "Courgette": "courgette", "Aubergine": "aubergine", "Épinards": "spinach",
       "Haricots verts": "green beans", "Citron": "lemon", "Pommes": "apples", "Bananes": "bananas",
       "Chocolat": "chocolate", "Huile d'olive": "olive oil", "Pain": "bread", "Lentilles": "lentils",
       "Pois chiches": "chickpeas", "Lardons / Bacon": "bacon", "Jambon": "ham", "Coco": "coconut milk"}


def recipes():
    st.subheader("🍳 Recettes selon ton frigo")
    st.radio("Langue des recettes", ["Français", "English"], horizontal=True, key="lang")
    sel = st.multiselect("Ingrédients que tu as", list(ING))
    extra = st.text_input("Autres (en anglais, séparés par des virgules)")
    names = [ING[s] for s in sel] + [e.strip().replace(" ", "_") for e in extra.split(",") if e.strip()]
    if st.session_state.get("rid"):
        if st.button("← Retour aux propositions"):
            st.session_state.rid = None
            st.rerun()
        d = (fetch("https://www.themealdb.com/api/json/v1/1/lookup.php", {"i": st.session_state.rid}) or {}).get("meals")
        if not d:
            return st.error("Recette introuvable.")
        m = d[0]
        st.header(fr(m["strMeal"]))
        c1, c2 = st.columns([1, 2])
        c1.image(m["strMealThumb"])
        lines = [f"{(m.get('strMeasure'+str(i)) or '').strip()} {m['strIngredient'+str(i)].strip()}"
                 for i in range(1, 21) if (m.get("strIngredient" + str(i)) or "").strip()]
        c1.markdown("**Ingrédients**\n\n" + "\n".join("- " + l for l in fr("\n".join(lines)).split("\n")))
        c2.markdown("**Préparation**")
        c2.write(fr(m["strInstructions"]))
        return
    if not names:
        return st.info("Sélectionne au moins un ingrédient.")
    count = {}
    for i in names:
        for m in (fetch("https://www.themealdb.com/api/json/v1/1/filter.php", {"i": i}) or {}).get("meals") or []:
            c = count.setdefault(m["idMeal"], {"m": m, "n": 0})
            c["n"] += 1
    ranked = sorted(count.values(), key=lambda x: -x["n"])[:12]
    if not ranked:
        return st.warning("Aucune recette trouvée avec ces ingrédients.")
    cols = st.columns(3)
    for k, c in enumerate(ranked):
        with cols[k % 3]:
            st.image(c["m"]["strMealThumb"])
            st.markdown(f"**{fr(c['m']['strMeal'])}**  \n{c['n']}/{len(names)} ingrédients")
            if st.button("Voir la recette", key="r" + c["m"]["idMeal"]):
                st.session_state.rid = c["m"]["idMeal"]
                st.rerun()


# ───────────────────────── PARIS SPORTIFS ─────────────────────────
FD = "https://api.football-data.org/v4"
COMPS = {"Ligue 1": "FL1", "Premier League": "PL", "Liga": "PD", "Bundesliga": "BL1", "Serie A": "SA",
         "Ligue des champions": "CL", "Coupe du monde": "WC", "Euro": "EC", "Eredivisie": "DED",
         "Primeira Liga": "PPL", "Championship": "ELC"}


def fd(path, params=None):
    return fetch(FD + path, params, {"X-Auth-Token": secret("FOOTBALL_DATA_KEY")})


def pois(l, k):
    return math.exp(-l) * l ** k / math.factorial(k)


def probs(lh, la):
    h = d = a = 0
    for i in range(10):
        for j in range(10):
            p = pois(lh, i) * pois(la, j)
            if i > j: h += p
            elif i == j: d += p
            else: a += p
    s = h + d + a
    return h / s, d / s, a / s


@st.cache_data(ttl=3600, show_spinner=False)
def wx(city, iso):
    g = fetch("https://geocoding-api.open-meteo.com/v1/search", {"name": city, "count": 1, "language": "fr"})
    r = (g or {}).get("results")
    if not r:
        return None
    f = fetch("https://api.open-meteo.com/v1/forecast", {"latitude": r[0]["latitude"], "longitude": r[0]["longitude"],
              "hourly": "precipitation,wind_speed_10m,temperature_2m", "timezone": "UTC", "forecast_days": 10})
    t = iso[:13] + ":00"
    if not f or t not in f["hourly"]["time"]:
        return None
    i = f["hourly"]["time"].index(t)
    h = f["hourly"]
    return h["precipitation"][i], h["wind_speed_10m"][i], h["temperature_2m"][i]


def strengths(code):
    t, sc = {}, {}
    for s in (fd(f"/competitions/{code}/standings") or {}).get("standings", []):
        if s.get("type") == "TOTAL":
            for r in s["table"]:
                t[r["team"]["id"]] = (r["goalsFor"], r["goalsAgainst"], r["playedGames"])
    for p in (fd(f"/competitions/{code}/scorers", {"limit": 100}) or {}).get("scorers", []):
        sc.setdefault(p["team"]["id"], p)
    gp = sum(v[2] for v in t.values())
    avg = sum(v[0] for v in t.values()) / gp if gp else 1.35
    return t, sc, avg


def rates(t, tid, avg):
    gf, ga, p = t.get(tid, (0, 0, 0))
    w = p / (p + 4)
    return w * gf / max(p, 1) + (1 - w) * avg, w * ga / max(p, 1) + (1 - w) * avg


def sports():
    st.subheader("⚽ Pronostics (modèle statistique)")
    if not secret("FOOTBALL_DATA_KEY"):
        return st.warning("Ajoute ta clé gratuite football-data.org dans les *Secrets* Streamlit : FOOTBALL_DATA_KEY.")
    sel = st.multiselect("Compétitions (3-4 max conseillé : limite de l'API gratuite)", list(COMPS),
                         default=["Ligue 1", "Ligue des champions", "Premier League"])
    days = st.slider("Jours à venir", 1, 9, 4)
    if not sel:
        return
    t0 = now().date()
    m = fd("/matches", {"dateFrom": t0.isoformat(), "dateTo": (t0 + dt.timedelta(days + 1)).isoformat(),
                        "competitions": ",".join(COMPS[s] for s in sel)})
    if m is None:
        return st.error("API indisponible ou limite atteinte (10 requêtes/min). Réessaie dans 1 minute.")
    fin = fd("/matches", {"dateFrom": (t0 - dt.timedelta(10)).isoformat(), "dateTo": t0.isoformat(), "status": "FINISHED"}) or {}
    last = {}
    for x in fin.get("matches", []):
        d = dt.datetime.fromisoformat(x["utcDate"].replace("Z", "+00:00")).date()
        for k in ("homeTeam", "awayTeam"):
            last[x[k]["id"]] = max(last.get(x[k]["id"], d), d)
    S, rows = {}, []
    for x in m.get("matches", []):
        if x["status"] not in ("SCHEDULED", "TIMED"):
            continue
        code = x["competition"]["code"]
        S.setdefault(code, strengths(code))
        t, sc, avg = S[code]
        h, a = x["homeTeam"], x["awayTeam"]
        if not h.get("id") or not a.get("id"):
            continue
        ah, dh = rates(t, h["id"], avg)
        aa, da = rates(t, a["id"], avg)
        ko = dt.datetime.fromisoformat(x["utcDate"].replace("Z", "+00:00")).astimezone(TZ)
        rest = {}
        for k, tm in (("h", h), ("a", a)):
            rest[k] = (ko.date() - last[tm["id"]]).days if tm["id"] in last else None
        if rest["h"] is not None and rest["h"] <= 3: ah *= 0.94
        if rest["a"] is not None and rest["a"] <= 3: aa *= 0.94
        lh, la = ah * da / avg * 1.1, aa * dh / avg * 0.95
        w = wx(h.get("shortName") or h["name"], x["utcDate"])
        if w and (w[0] >= 3 or w[1] >= 35):
            lh, la = lh * 0.93, la * 0.93
        ph, pd_, pa = probs(lh, la)
        pick, conf = max((("Victoire " + (h.get("shortName") or h["name"]), ph), ("Match nul", pd_),
                          ("Victoire " + (a.get("shortName") or a["name"]), pa)), key=lambda z: z[1])
        best = (None, 0)
        for tm, lam in ((h, lh), (a, la)):
            p = sc.get(tm["id"])
            gf = t.get(tm["id"], (0,))[0]
            if p and gf:
                pr = 1 - math.exp(-lam * (p["goals"] / gf))
                if pr > best[1]: best = (p["player"]["name"], pr)
        rows.append({"Date": ko.strftime("%d/%m/%Y"), "Heure": ko.strftime("%H:%M"), "Compétition": x["competition"]["name"],
                     "Match": f"{h.get('shortName') or h['name']} - {a.get('shortName') or a['name']}",
                     "Pronostic": pick, "Confiance %": round(conf * 100, 1),
                     "Favori": (h.get("shortName") or h["name"]) if ph >= pa else (a.get("shortName") or a["name"]),
                     "Victoire %": round(max(ph, pa) * 100, 1),
                     "ID": x["id"], "Côté": "HOME_TEAM" if ph >= pa else "AWAY_TEAM", "UTC": x["utcDate"],
                     "Dom/Nul/Ext %": f"{ph*100:.0f} / {pd_*100:.0f} / {pa*100:.0f}",
                     "Buteur probable": best[0] or "n/d", "% but": round(best[1] * 100, 1),
                     "Météo": f"{w[2]:.0f}°C, pluie {w[0]:.1f}mm, vent {w[1]:.0f}km/h" if w else "n/d",
                     "Repos (j) D/E": f"{rest['h'] if rest['h'] is not None else '?'} / {rest['a'] if rest['a'] is not None else '?'}"})
    if not rows:
        return st.info("Aucun match à venir sur cette période.")
    df = pd.DataFrame(rows).sort_values("Confiance %", ascending=False).reset_index(drop=True)
    df.index += 1
    top = df.sort_values("Victoire %", ascending=False).head(10).reset_index(drop=True)
    top.index += 1
    st.markdown("### 🏆 Top 10 des plus fortes probabilités de victoire")
    view = st.radio("Affichage du classement", ["Cartes", "Tableau"], horizontal=True, key="view")
    if view == "Cartes":
        for i, r in top.iterrows():
            st.markdown(
                f'<div class="card"><b>#{i} {escape(r["Match"])}</b>'
                f'<div class="muted">{r["Date"]} à {r["Heure"]} · {escape(r["Compétition"])}</div>'
                f'<div style="margin:6px 0">Favori : <b>{escape(r["Favori"])}</b> : {r["Victoire %"]:.0f} %</div>'
                f'<div class="bar"><div style="width:{r["Victoire %"]}%"></div></div>'
                f'<div class="muted" style="margin-top:6px">⚽ {escape(r["Buteur probable"])} ({r["% but"]:.0f} %)</div></div>',
                unsafe_allow_html=True)
    else:
        st.dataframe(top[["Date", "Heure", "Compétition", "Match", "Favori", "Victoire %", "Buteur probable", "% but"]],
                 use_container_width=True, column_config={
        "Victoire %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        "% but": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)})
    st.markdown("### 📋 Tous les matchs")
    sel_df = df.copy()
    sel_df.insert(0, "Suivre", False)
    ed = st.data_editor(sel_df, use_container_width=True, key="ed_matchs",
                        disabled=[c for c in sel_df.columns if c != "Suivre"],
                        column_order=["Suivre", "Date", "Heure", "Compétition", "Match", "Favori", "Victoire %", "Pronostic",
                                      "Confiance %", "Dom/Nul/Ext %", "Buteur probable", "% but", "Météo", "Repos (j) D/E"],
                        column_config={"Suivre": st.column_config.CheckboxColumn("Suivre"),
        "Victoire %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        "Confiance %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        "% but": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)})
    if st.button("💾 Enregistrer les matchs cochés (victoire du favori)"):
        db = load_db()
        ids = {e["id"] for e in db}
        n = 0
        for _, r in ed[ed["Suivre"]].iterrows():
            if int(r["ID"]) in ids:
                continue
            db.append({"id": int(r["ID"]), "date": f"{r['Date']} {r['Heure']}", "competition": r["Compétition"],
                       "match": r["Match"], "favori": r["Favori"], "proba": float(r["Victoire %"]), "cote": r["Côté"],
                       "utc": r["UTC"], "resultat": "En attente", "score": ""})
            n += 1
        save_db()
        st.success(f"{n} match(s) enregistré(s). Va dans l'onglet 📊 Suivi.")
    st.caption("Modèle : loi de Poisson (buts marqués/encaissés, avantage domicile), fatigue (≤3 jours de repos), "
               "météo (pluie/vent). Non pris en compte : blessures et cotes des bookmakers. "
               "Aucun pronostic n'est sûr : joue avec modération, 18+. Aide : 09 74 75 13 13.")


# ───────────────────────── CRYPTO ─────────────────────────
def crypto():
    st.subheader("₿ Cryptos : momentum du moment")
    d = fetch("https://api.coingecko.com/api/v3/coins/markets", {"vs_currency": "eur", "order": "market_cap_desc",
              "per_page": 100, "page": 1, "price_change_percentage": "1h,24h,7d,30d"})
    if not d:
        return st.error("CoinGecko indisponible, réessaie dans un instant.")
    g = lambda c, k: c.get(f"price_change_percentage_{k}_in_currency") or 0
    rows = []
    for c in d:
        vr = (c["total_volume"] or 0) / (c["market_cap"] or 1)
        rows.append({"Crypto": f"{c['name']} ({c['symbol'].upper()})", "Prix €": c["current_price"], "1h %": g(c, "1h"),
                     "24h %": g(c, "24h"), "7j %": g(c, "7d"), "30j %": g(c, "30d"), "Volume/Cap": round(vr, 3),
                     "Score": round(.15 * g(c, "1h") + .4 * g(c, "24h") + .3 * g(c, "7d") + .15 * g(c, "30d"), 2),
                     "Baleines ?": "🐋 volume anormal" if vr > .25 else ""})
    df = pd.DataFrame(rows).sort_values("Score", ascending=False).head(25).reset_index(drop=True)
    df.index += 1
    fg = (fetch("https://api.alternative.me/fng/", {"limit": 1}) or {}).get("data", [{}])[0]
    if fg:
        st.metric("Indice peur & cupidité", f"{fg['value']}/100", fg["value_classification"])
    st.dataframe(df, use_container_width=True)
    st.caption(f"Mis à jour le {now():%d/%m/%Y à %H:%M:%S}. 🐋 = volume 24h > 25 % de la capitalisation (indice indirect de gros mouvements, "
               "pas un suivi on-chain). Très risqué : ne mise que ce que tu peux perdre.")
    st.markdown("**Actualités politiques / réglementaires**")
    xml = fetch("https://news.google.com/rss/search", {"q": "bitcoin (régulation OR SEC OR ETF OR Trump OR BCE) when:2d",
                "hl": "fr", "gl": "FR", "ceid": "FR:fr"}, raw=True)
    try:
        for it in ET.fromstring(xml).iter("item"):
            st.markdown(f"- [{it.findtext('title')}]({it.findtext('link')})  \n  <small>{it.findtext('pubDate')}</small>",
                        unsafe_allow_html=True)
            if st.session_state.setdefault("n", 0) > 99: break
    except Exception:
        st.info("Actualités indisponibles.")


# ───────────────────────── ENTREPRISES BAS-RHIN ─────────────────────────
NAF = {"Restaurants": "56.10A,56.10C", "Coiffure": "96.02A", "Beauté / esthétique": "96.02B", "Hôtels": "55.10Z",
       "Boulangeries": "10.71C,10.71D", "Salles de sport": "93.13Z", "Immobilier": "68.31Z",
       "Concessions auto": "45.11Z", "Fleuristes": "47.76Z", "Prêt-à-porter": "47.71Z"}
VISU = {"Restaurants", "Coiffure", "Beauté / esthétique", "Salles de sport", "Fleuristes", "Prêt-à-porter"}


def prospects():
    st.subheader("📣 Entreprises du Bas-Rhin (67) à démarcher pour du community management")
    sec = st.multiselect("Secteurs", list(NAF), default=["Restaurants", "Coiffure", "Beauté / esthétique"])
    ville = st.text_input("Filtrer par commune (optionnel)").strip().lower()
    rows = []
    for s in sec:
        for page in (1, 2, 3):
            d = fetch("https://recherche-entreprises.api.gouv.fr/search", {"departement": "67", "activite_principale": NAF[s],
                      "etat_administratif": "A", "per_page": 25, "page": page})
            for r in (d or {}).get("results", []):
                sg = r.get("siege") or {}
                eff = r.get("tranche_effectif_salarie")
                if eff not in (None, "NN", "00", "01", "02", "03"):
                    continue
                cr = r.get("date_creation") or ""
                age = (now().year - int(cr[:4])) if cr[:4].isdigit() else 99
                score = 40 + (25 if age <= 3 else 10 if age <= 8 else 0) + (15 if eff in (None, "NN", "00", "01", "02") else 5) + (15 if s in VISU else 5)
                com = sg.get("libelle_commune") or ""
                if ville and ville not in com.lower():
                    continue
                nom = r.get("nom_complet")
                rows.append({"Entreprise": nom, "Secteur": s, "Commune": com, "Créée le": cr, "Score besoin CM": score,
                             "Vérifier sa présence": f"https://www.google.com/search?q={requests.utils.quote(f'{nom} {com} instagram facebook')}"})
    if not rows:
        return st.info("Aucun résultat.")
    df = pd.DataFrame(rows).drop_duplicates("Entreprise").sort_values("Score besoin CM", ascending=False).reset_index(drop=True)
    st.dataframe(df, use_container_width=True, column_config={
        "Vérifier sa présence": st.column_config.LinkColumn(display_text="Chercher"),
        "Score besoin CM": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d")})
    st.caption("Source : base SIRENE (API Recherche d'entreprises). Score = secteur visuel + jeune + petite structure. "
               "Vérifie leurs réseaux avant de les contacter.")


# ───────────────────────── ACTUS ─────────────────────────
NEWS = {"🌍 À la une": None, "⚽ Football": "football", "₿ Crypto": "bitcoin OR crypto",
        "📍 Alsace": "Strasbourg OR Alsace OR Bas-Rhin", "💶 Économie": "économie France",
        "📣 Marketing": "community management OR réseaux sociaux OR Instagram"}


def actus():
    st.subheader("📰 Actualités")
    cat = st.radio("Catégorie", list(NEWS), horizontal=True, key="cat")
    q = NEWS[cat]
    geo = {"hl": "fr", "gl": "FR", "ceid": "FR:fr"}
    xml = fetch("https://news.google.com/rss/search", {"q": f"{q} when:2d", **geo}, raw=True) if q \
        else fetch("https://news.google.com/rss", geo, raw=True)
    try:
        items = list(ET.fromstring(xml).iter("item"))[:15]
    except Exception:
        return st.error("Actualités indisponibles pour le moment.")
    for it in items:
        try:
            d = parsedate_to_datetime(it.findtext("pubDate")).astimezone(TZ).strftime("%d/%m/%Y à %H:%M")
        except Exception:
            d = ""
        st.markdown(f'<div class="card"><a href="{escape(it.findtext("link") or "")}" target="_blank" '
                    f'style="color:inherit;font-weight:600;text-decoration:none">{escape(it.findtext("title") or "")}</a>'
                    f'<div class="muted">{escape(it.findtext("source") or "")} · {d}</div></div>', unsafe_allow_html=True)
    st.caption(f"Actualisé le {now():%d/%m/%Y à %H:%M:%S} (heure de Paris, cache 10 min). Source : Google Actualités.")


# ───────────────────────── SUIVI ─────────────────────────
DB = "suivi_paris.json"


def load_db():
    if "db" not in st.session_state:
        try:
            st.session_state.db = json.load(open(DB, encoding="utf-8"))
        except Exception:
            st.session_state.db = []
    return st.session_state.db


def save_db():
    try:
        json.dump(st.session_state.db, open(DB, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def suivi():
    st.subheader("📊 Suivi : taux de réussite et d'échec")
    db = load_db()
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Sauvegarder (JSON)", json.dumps(db, ensure_ascii=False, indent=1), "suivi_paris.json", "application/json")
    up = c2.file_uploader("Restaurer une sauvegarde", type="json")
    if up and st.button("Importer la sauvegarde"):
        try:
            ids = {e["id"] for e in db}
            db.extend(e for e in json.load(up) if e["id"] not in ids)
            save_db()
            st.rerun()
        except Exception:
            st.error("Fichier invalide.")
    if not db:
        return st.info("Coche des matchs dans l'onglet Paris sportifs, puis enregistre-les.")
    if st.button("🔄 Mettre à jour les résultats"):
        limit = now().astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        n = 0
        for e in db:
            if e["resultat"] == "En attente" and e["utc"] < limit:
                m = fd(f"/matches/{e['id']}")
                if m and m.get("status") == "FINISHED":
                    ft = m["score"]["fullTime"]
                    e["score"] = f"{ft['home']}-{ft['away']}"
                    e["resultat"] = "Gagné" if m["score"]["winner"] == e["cote"] else "Perdu"
                n += 1
                if n >= 8:
                    st.info("8 matchs vérifiés (limite de l'API) : reclique dans 1 minute pour la suite.")
                    break
        save_db()
        st.rerun()
    df = pd.DataFrame(db)
    done = df[df.resultat != "En attente"]
    if len(done):
        ok = (done.resultat == "Gagné").mean() * 100
        a, b, c, d = st.columns(4)
        a.metric("Matchs terminés", len(done))
        b.metric("✅ Réussite", f"{ok:.0f}%")
        c.metric("❌ Échec", f"{100 - ok:.0f}%")
        d.metric("Proba moyenne annoncée", f"{done.proba.mean():.0f}%")
        done = done.assign(Tranche=pd.cut(done.proba, [0, 50, 60, 70, 101], labels=["<50%", "50-60%", "60-70%", ">70%"], right=False))
        st.markdown("**Réussite selon la probabilité annoncée** (si le modèle est fiable, elle doit suivre la probabilité)")
        st.dataframe(done.groupby("Tranche", observed=True).agg(
            Matchs=("resultat", "size"), **{"Réussite %": ("resultat", lambda s: round((s == "Gagné").mean() * 100))}),
            use_container_width=True)
    st.dataframe(df[["date", "competition", "match", "favori", "proba", "resultat", "score"]].rename(columns={
        "date": "Date", "competition": "Compétition", "match": "Match", "favori": "Favori", "proba": "Proba %",
        "resultat": "Résultat", "score": "Score"}), use_container_width=True)
    st.caption("Un nul compte comme un échec (pari « victoire du favori »). Le buteur n'est pas vérifié automatiquement.")
    if st.button("🗑️ Tout effacer"):
        st.session_state.db = []
        save_db()
        st.rerun()


# ───────────────────────── TETRIS ─────────────────────────
TETRIS = """
<div style="text-align:center;font-family:sans-serif;color:#00b4ff">
<canvas id=c width=200 height=400 style="border:2px solid #00b4ff;box-shadow:0 0 22px #00b4ff;background:#000;max-width:100%"></canvas>
<div style="margin:6px">Score : <b id=s>0</b> <button onclick="init()" style="background:#06142a;color:#00b4ff;border:1px solid #00b4ff;border-radius:6px;padding:4px 10px">Rejouer</button></div>
<div style="display:flex;gap:8px;justify-content:center">
<button onclick="mv(-1)">◀</button><button onclick="rot()">⟳</button><button onclick="mv(1)">▶</button><button onclick="dn()">▼</button></div></div>
<style>button{font-size:24px;width:64px;height:52px;background:#06142a;color:#00b4ff;border:1px solid #00b4ff;border-radius:10px}</style>
<script>
const x=document.getElementById('c').getContext('2d'),W=10,H=20,S=20;
const P=[[[1,1,1,1]],[[1,1],[1,1]],[[0,1,0],[1,1,1]],[[1,0,0],[1,1,1]],[[0,0,1],[1,1,1]],[[0,1,1],[1,1,0]],[[1,1,0],[0,1,1]]];
const K=['#00e5ff','#ffd700','#b388ff','#2979ff','#ff9100','#00e676','#ff1744'];
let b,sc,over,p,T;
function col(m,px,py){return m.some((r,j)=>r.some((v,i)=>v&&(px+i<0||px+i>=W||py+j>=H||(py+j>=0&&b[py+j][px+i]))))}
function nw(){let i=Math.random()*7|0;p={m:P[i],c:K[i],x:3,y:0};if(col(p.m,3,0))over=true}
function rot(){if(over)return;let m=p.m[0].map((_,i)=>p.m.map(r=>r[i]).reverse());if(!col(m,p.x,p.y))p.m=m;dr()}
function mv(d){if(over)return;if(!col(p.m,p.x+d,p.y))p.x+=d;dr()}
function dn(){if(over)return;if(!col(p.m,p.x,p.y+1))p.y++;else{
p.m.forEach((r,j)=>r.forEach((v,i)=>{if(v&&p.y+j>=0)b[p.y+j][p.x+i]=p.c}));
b=b.filter(r=>r.some(v=>!v));let n=H-b.length;sc+=[0,100,300,500,800][n];
while(b.length<H)b.unshift(Array(W).fill(0));nw();document.getElementById('s').textContent=sc}dr()}
function dr(){x.fillStyle='#000';x.fillRect(0,0,200,400);
b.forEach((r,j)=>r.forEach((v,i)=>{if(v){x.fillStyle=v;x.fillRect(i*S,j*S,S-1,S-1)}}));
if(!over){x.fillStyle=p.c;p.m.forEach((r,j)=>r.forEach((v,i)=>{if(v)x.fillRect((p.x+i)*S,(p.y+j)*S,S-1,S-1)}))}
else{x.fillStyle='#fff';x.font='24px sans-serif';x.fillText('GAME OVER',35,200)}}
function init(){b=Array.from({length:H},()=>Array(W).fill(0));sc=0;over=false;nw();document.getElementById('s').textContent=0;
clearInterval(T);T=setInterval(dn,500);dr()}
document.addEventListener('keydown',e=>{const k={ArrowLeft:()=>mv(-1),ArrowRight:()=>mv(1),ArrowUp:rot,ArrowDown:dn}[e.key];if(k){e.preventDefault();k()}});
init();
</script>"""


def tetris():
    st.subheader("🎮 Tetris")
    components.html(TETRIS.replace("#00b4ff", PAL.get(st.session_state.get("theme"), PAL["🔵 Bleu néon"])["A"]), height=560)


# ───────────────────────── PAGE ─────────────────────────
st.title("⚡ Hub Perso")
st.radio("Thème", list(PAL), horizontal=True, key="theme", label_visibility="collapsed")
st.caption(f"📅 {now():%A %d/%m/%Y} · 🕒 {now():%H:%M:%S} (heure de Paris)")
t1, t2, t6, t3, t7, t4, t5 = st.tabs(["🍳 Recettes", "⚽ Paris", "📊 Suivi", "₿ Cryptos", "📰 Actus", "📣 Prospects", "🎮 Tetris"])
with t1: recipes()
with t2: sports()
with t3: crypto()
with t4: prospects()
with t5: tetris()
with t6: suivi()
with t7: actus()
