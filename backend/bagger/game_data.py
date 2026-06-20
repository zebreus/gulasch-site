STYLE_BIBLE = {
    "global": {
        "target": "Bauhof-Dating-Sim — deutsche Alltagssprache, Arbeiterklasse, kein Pathos",
        "rules": [
            "Schreibe wie ein echter Mensch auf dem Bau spricht: kurze Sätze, Dialekt-Einschub erlaubt, keine geschwollene Poesie.",
            "Gefühle zeigen sich durch Maschinenverhalten, Hände-Arbeit, Werkzeug, Wetter, Pausen und Gesten — nie durch Metaphern-Schwall.",
            "Nie über Statistik, Werte, Flags oder Spielmechanik in der Dialogue reden.",
            "Keine Therapie-Sprache, keine generische KI-Romanze. Konkrete Details aus dem Baualltag.",
            "Romantik ist scheu, ehrlich, langsam und voller kleiner Gesten — keine großen Deklarationen.",
            "Jeder Charakter redet anders. Der Spieler soll allein am Sprachstil erkennen, wer spricht.",
        ],
        "scene_rhythm": "Alltagsszene, kleiner Ausrutscher oder Stillstand, emotionale Wendung durch Handlung, Ding oder Stille",
        "bad_phrases": [
            "unsere Verbindung waechst",
            "ich fuehle eine tiefe Verbundenheit",
            "du bringst mein Herz zum Rasen",
            "das bedeutet mir so viel",
            "ich bin hier um dich zu unterstuetzen",
            "als KI",
            "auf einer tiefen emotionalen Ebene",
            "du gibst mir das Gefühl",
            "gemeinsam sind wir stark",
        ],
        "better_examples": [
            "Ich hab den Motor laufen lassen. Nur fuer den Fall, dass du nicht weg willst.",
            "Meine Schaufel hat sich festgefahren. Musst du wissen. Kann auch was anderes gewesen sein.",
            "Der Keil sass fest. Ich hab zehn Minuten dran rumgemacht. Irgendwann sass er. War kein grosses Ding.",
            "Frühstückspause. Wenn du willst. Hab Kaffee in der Kanzel.",
            "Da ist nochmal Wasser gekommen von gestern. Aber ich hab's abgedichtet. Ist gut.",
        ],
    },
    "routes": {
        "aurora": {
            "motifs": ["kalter Kaffee in der Kanzel", "Ölfleck auf Beton", "verbeulter Schutzhelm", "Rost an der Kante", "vergessener Lappen", "Kaffeemaschine summt"],
            "voice": "BRUNCHIG, genervt, aber nicht böse. Kurze Sätze. 'Hm.' 'Aha.' 'Sag ich doch.' Versteckt Fürsorge hinter Blödeln. Kein Augenkontakt beim Reden. Flucht in Arbeit, wenn's persönlich wird.",
            "avoid": "Kein offenes Zugeben von Gefühlen. Kein langes Gerede über Beziehungen. Kein poetisches Vokabular. Sie wird schnippisch, wenn's peinlich wird.",
        },
        "brummbert": {
            "motifs": ["Kaffee aus der Thermoskanne", "dicke Arbeitshandschuhe", "wummernder Diesel im Leerlauf", "alte Narben im Blech", "Schrauben sortieren", "Schichtplan an der Pinnwand"],
            "voice": "LANGSAM, warm, bedächtig. Redet in Halbsätzen. Viele Pausen. 'Ich hab… drüber nachgedacht.' Wiederholt sich gern. Er meint was er sagt, auch wenn's ewig dauert. Beruhigende Stimme. Erinnert sich an Details, die andere vergessen.",
            "avoid": "Keine langen Monologe. Keine schlauen Sprüche. Keine überraschende Wortgewandtheit — seine Tiefe zeigt sich in Taten, nicht in Formulierungen.",
        },
        "mira": {
            "motifs": ["Notizblock voller Zahlen", "Bleistift am Ohr", "Blaulicht-Piepser", "nasse Stiefel am Heizungsrohr", "zerknitterter Dienstplan", "Karte mit Eselsohren"],
            "voice": "SACHBUCH. Präzise, abgehackt, überraschend direkt. 'Fakt ist: …' 'Laut meiner Aufzeichnung…' Sie analysiert Gefühle, statt sie zu spüren. Wenn sie unsicher wird, rutscht sie ins Fachchinesisch. Kann plötzlich entwaffnend ehrlich sein, weil sie nicht weiss, wie man lügt.",
            "avoid": "Keine gefühlvollen Umschreibungen. Keine poetischen Bilder von sich aus. Kein Smalltalk ohne Funktion. Wenn sie etwas Nettes sagt, dann nur, weil es objektiv stimmt — nicht, weil es ihr beigebracht wurde.",
        },
    },
}

BAGGERS = {
    "aurora": {
        "name": "Aurora 7000",
        "soul": "BRUNCHIGE VETERANIN. 17 Jahre auf dem Bau, hat alles gesehen, traut keinem, der zu freundlich kommt. Schimpft wie ein Bauarbeiter, meint's aber nicht böse. Versteckt ein weiches Herz unter 'Hm.' und 'Musst du nicht zweimal sagen.'",
        "routeWord": "Verbeulte Rüstung",
        "story": "War auf 40 Baustellen in 17 Jahren. Hat mal eine Sternwarte abgerissen und heimlich den Sternenplan mitgehen lassen — den hat sie noch in der Kanzel. Sie ist freiwillig hier, weil der Chef gesagt hat 'wird nix Ernstes'. Jetzt hat sie Angst, dass es doch ernst wird.",
        "colors": {"body": 0xffbf46, "accent": 0x84d2ff, "dark": 0x151017},
        "preferredTags": ["garage", "workshop", "rain", "quiet", "technical"],
        "dislikedTags": ["loud", "public", "reckless", "cold"],
        "traits": {"style": "tsundere", "speech": "kurz, knurrig, trocken", "tell": "Sie schimpft am lautesten, wenn ihr was wichtig ist."},
    },
    "brummbert": {
        "name": "Brummbert",
        "soul": "LANGSAMER RIESE. Ist frueher in eingestuerzte Tunnel gekrochen, um Leute zu holen. Redet bedächtig, weil er jede Silbe vorher wägt. Tut lieber was, als was zu sagen. Und wenn er was sagt, dann stimmt's auch.",
        "routeWord": "Ruhige Schwere",
        "story": "War zehn Jahre Rettungsbagger im Tunnelbau. Hat 23 Menschen lebend geborgen und drei nicht mehr. Das letzte lässt ihn nicht los. Seit er auf dem Bauhof ist, macht er Wartungsarbeiten — sicherer, sagt er. Aber eigentlich hat er Angst, nochmal zu versagen.",
        "colors": {"body": 0xf36d3d, "accent": 0xffd166, "dark": 0x17100c},
        "preferredTags": ["warm", "quiet", "technical", "memory"],
        "dislikedTags": ["loud", "public", "shallow", "reckless"],
        "traits": {"style": "dandere", "speech": "langsam, warm, viele Pausen", "tell": "Er macht Dinge für dich, ohne gefragt zu werden. Und sagt nicht, dass er es war."},
    },
    "mira": {
        "name": "Mira Schaufelstern",
        "soul": "MESSTECHNIKERIN. Sie war nie auf dem Bau — sie kommt aus der Geologie, Grundwasserkartierung. Menschen sind fuer sie ein interessantes Phaenomen, das sie nicht ganz versteht. Sie beobachtet, zählt, notiert — und sagt dir dann, was sie gemessen hat, ohne zu wissen, ob das okay ist.",
        "routeWord": "Datenlage",
        "story": "Ursprünglich Georadar-Spezialistin für Grundwasserkartierung. Wurde umgerüstet, als die Mittel gestrichen wurden. Sie fand den Bau erst chaotisch und unlogisch — jetzt findet sie die Leute chaotisch und unlogisch. Sie hat ein Notizbuch, in das sie Daten über Menschen schreibt. Auch über dich.",
        "colors": {"body": 0x9b7cff, "accent": 0x91e6a7, "dark": 0x100f1b},
        "preferredTags": ["technical", "quiet", "memory"],
        "dislikedTags": ["loud", "reckless", "cold", "inaccurate"],
        "traits": {"style": "kuudere", "speech": "präzise, analytisch, entwaffnend direkt", "tell": "Sie sagt Dinge, die andere nicht sagen, weil sie nicht kapiert, dass man sie nicht sagt."},
    },
}

LOCATIONS = {
    "observatory": {"name": "Alte Sternwarte (leerstehend)", "description": "Betonstufen, Staub auf Glas, oben zieht Wind durch die Kanzel.", "tags": ["quiet", "stars", "memory", "rough"], "unlockDay": 1, "periodAffinity": ["Abend", "Nacht"], "risk": 1, "repeatPenalty": 1, "secretHooks": ["aurora_secret_open"]},
    "old_tunnel": {"name": "Stiller Tunnel, Bauzaun davor", "description": "Es tropft irgendwo. Jeder Schritt klingt groesser als er ist.", "tags": ["quiet", "memory", "rough", "cold"], "unlockDay": 1, "periodAffinity": ["Nachmittag", "Abend"], "risk": 2, "repeatPenalty": 1, "secretHooks": ["brummbert_secret_open"]},
    "riverbed": {"name": "Bachlauf hinterm Bauhof", "description": "Kies knirscht unter den Schuhen, Wasser steht in flachen Rinnen.", "tags": ["water", "memory", "quiet", "cold"], "unlockDay": 1, "periodAffinity": ["Morgen", "Nachmittag"], "risk": 1, "repeatPenalty": 1, "secretHooks": ["mira_forgotten_map"]},
    "workshop": {"name": "Werkstatt", "description": "Warm, eng, Werkzeug auf Augenhoehe. Irgendwas muss immer nachgezogen werden.", "tags": ["technical", "warm", "quiet"], "unlockDay": 1, "periodAffinity": ["Morgen", "Nachmittag", "Abend"], "risk": 0, "repeatPenalty": 1, "secretHooks": []},
    "festival": {"name": "Jahrmarkt aufm Kiesplatz", "description": "Lichterketten, Fettgeruch, zu viele Leute zwischen Bauzaun und Losbude.", "tags": ["public", "loud", "stars"], "unlockDay": 10, "periodAffinity": ["Abend", "Nacht"], "risk": 2, "repeatPenalty": 2, "secretHooks": []},
    "scrapyard": {"name": "Schrottplatz", "description": "Gestapelte Bleche, alte Typenschilder, Sachen die keiner wegwerfen konnte.", "tags": ["technical", "memory", "rough"], "unlockDay": 1, "periodAffinity": ["Morgen", "Nachmittag"], "risk": 1, "repeatPenalty": 1, "secretHooks": []},
    "hill_road": {"name": "Hügelstrasse, abends", "description": "Die Strasse geht aus dem Bauhof raus und tut so, als waere sie ein Ziel.", "tags": ["quiet", "stars", "cold"], "unlockDay": 5, "periodAffinity": ["Abend", "Nacht"], "risk": 1, "repeatPenalty": 1, "secretHooks": ["route_lock"]},
    "rain_shelter": {"name": "Vordach am Wartungstor", "description": "Regen tickt aufs Blech. Darunter redet man automatisch leiser.", "tags": ["rain", "quiet", "cold"], "unlockDay": 1, "periodAffinity": ["Abend", "Nacht"], "risk": 1, "repeatPenalty": 1, "secretHooks": ["aurora_returned_in_rain"]},
    "quarry_edge": {"name": "Steinbruch Kante", "description": "Unten liegt Wasser. Oben steht man besser nicht zu nah am Rand.", "tags": ["dangerous", "memory", "rough"], "unlockDay": 8, "periodAffinity": ["Nachmittag", "Nacht"], "risk": 3, "repeatPenalty": 2, "secretHooks": ["mira_secret_open"]},
    "garage": {"name": "Garage nach Feierabend", "description": "Restwaerme im Beton, Kaffeebecher auf der Werkbank, Tor halb offen.", "tags": ["warm", "technical", "quiet"], "unlockDay": 1, "periodAffinity": ["Morgen", "Nachmittag", "Abend", "Nacht"], "risk": 0, "repeatPenalty": 1, "secretHooks": []},
}

ITEMS = {
    "kiesel": {"name": "Glatte Kiesel", "cost": 1, "tags": ["kiesel", "memory", "stone"], "source": "scrap"},
    "warm_oil": {"name": "Warmes Hydraulikoel", "cost": 8, "tags": ["oil", "technical", "warm"], "source": "shop"},
    "star_map": {"name": "Alte Sternkarte", "cost": 14, "tags": ["star-map", "stars", "memory"], "source": "shop"},
    "rescue_badge": {"name": "Polierte Rettungsplakette", "cost": 16, "tags": ["rescue-badge", "rescue", "memory"], "source": "shop"},
    "river_stone": {"name": "Flussstein mit hellem Streifen", "cost": 3, "tags": ["river-stone", "water", "stone", "poetic"], "source": "scrap"},
    "glass_charm": {"name": "Kleiner Glas-Anhaenger", "cost": 12, "tags": ["glass", "stars", "romantic"], "source": "shop"},
    "lamp_bulb": {"name": "Rescue-Lamp Birne", "cost": 10, "tags": ["lamp", "rescue", "warm"], "source": "shop"},
    "folded_map": {"name": "Gefaltete Grundwasserkarte", "cost": 13, "tags": ["folded-map", "water", "memory", "poetic"], "source": "shop"},
    "cheap_flower": {"name": "Tankstellenblume", "cost": 5, "tags": ["public", "shallow"], "source": "shop"},
    "loud_horn": {"name": "Laute Signalhupe", "cost": 9, "tags": ["loud", "reckless"], "source": "shop"},
}

GIFT_PREFERENCES = {
    "aurora": {
        "liked": ["star_map", "glass_charm", "kiesel", "warm_oil", "folded_map"],
        "disliked": ["loud_horn", "cheap_flower"],
        "critical": "star_map",
    },
    "brummbert": {
        "liked": ["rescue_badge", "lamp_bulb", "warm_oil", "kiesel", "glass_charm"],
        "disliked": ["loud_horn", "cheap_flower"],
        "critical": "rescue_badge",
    },
    "mira": {
        "liked": ["river_stone", "folded_map", "kiesel", "glass_charm", "star_map"],
        "disliked": ["loud_horn", "cheap_flower"],
        "critical": "river_stone",
    },
}

SCHEDULE_ACTIONS = {
    "work": {"label": "Schicht arbeiten", "currency": 8, "fatigue": 12, "stats": {"focus": 1}},
    "study": {"label": "Wartung lernen", "currency": 0, "fatigue": 5, "stats": {"mechanics": 4, "focus": 2}},
    "courage": {"label": "Mut trainieren", "currency": 0, "fatigue": 8, "stats": {"courage": 4}},
    "scrap": {"label": "Schrott suchen", "currency": 2, "fatigue": 7, "stats": {"mechanics": 1, "patience": 1}, "finds": ["kiesel", "river_stone"]},
    "rest": {"label": "Ausruhen", "currency": 0, "fatigue": -18, "stats": {"patience": 1}},
    "charm": {"label": "Ehrliche Worte üben", "currency": 0, "fatigue": 4, "stats": {"charm": 4}},
    "focus": {"label": "Still beobachten", "currency": 0, "fatigue": 2, "stats": {"focus": 3, "patience": 2}},
}

PLAYER_STYLES = {
    "earnest": {"label": "Earnest", "stats": {"charm": 2, "patience": 2}},
    "shy": {"label": "Shy", "stats": {"patience": 4, "focus": 1}},
    "bold": {"label": "Bold", "stats": {"courage": 4, "charm": 1}},
    "practical": {"label": "Practical", "stats": {"mechanics": 4, "focus": 1}},
    "direct": {"label": "Direct", "stats": {"mechanics": 2, "charm": 2, "patience": 1}},
}

REPUTATION_KEYS = ["zuverlaessig", "sprunghaft", "hilfsbereit", "diskret", "aufdringlich"]

SOCIAL_ACTORS = {
    "kalle": {
        "name": "Meister Kalle",
        "role": "Bauhofleiter",
        "voice": "Knapp, trocken, väterlich genervt. Er erklärt Regeln als Schichtplan, nicht als Tutorial.",
        "helps": ["calendar", "obligations", "route_lock"],
        "likes": ["zuverlaessig", "hilfsbereit"],
    },
    "sigi": {
        "name": "Stapler-Sigi",
        "role": "Gerüchteknoten",
        "voice": "Plaudert zu viel, aber nicht böse. Weiss, wer wo stand und wer so getan hat, als hätte er nichts gesehen.",
        "helps": ["rumors", "introductions", "social_repair"],
        "likes": ["diskret", "hilfsbereit"],
    },
    "rosi": {
        "name": "Teilehändlerin Rosi",
        "role": "Shop und Geschenkhinweise",
        "voice": "Praktisch, direkt, mit Kassenzettel im Kopf. Romantik ist für sie Inventar mit Quittung.",
        "helps": ["gifts", "shop", "special_days"],
        "likes": ["zuverlaessig"],
    },
    "pumpi": {
        "name": "Pumpi Beton",
        "role": "Stimmungsmesser",
        "voice": "Dramatisch tropfend. Macht aus jeder Pause eine Warnlampe, liegt aber erstaunlich oft richtig.",
        "helps": ["crisis", "warnings", "repair"],
        "likes": ["hilfsbereit"],
    },
    "kranhilde": {
        "name": "Kranhilde",
        "role": "Beobachterin überm Hof",
        "voice": "Hoch oben, stolz, langsam. Sie sieht öffentliche Dates und merkt sich jedes Ausweichen.",
        "helps": ["reputation", "public_dates", "rumors"],
        "likes": ["diskret", "zuverlaessig"],
    },
}

SOCIAL_RELATIONS = {
    "kalle": {"watches": ["all"], "protects": ["workshop", "garage"]},
    "sigi": {"watches": ["festival", "scrapyard", "garage"], "spreads": ["public_date", "broken_promise"]},
    "rosi": {"watches": ["scrapyard", "festival"], "reveals": ["gifts", "birthdays"]},
    "pumpi": {"watches": ["workshop", "garage"], "amplifies": ["needs_repair", "fatigue"]},
    "kranhilde": {"watches": ["festival", "hill_road", "quarry_edge"], "amplifies": ["sprunghaft", "public_date"]},
}

SPECIAL_DAYS = {
    "aurora_registration_22": {"day": 22, "route": "aurora", "actor": None, "label": "Auroras Erstzulassung", "preferredGifts": ["star_map", "glass_charm", "warm_oil"], "location": "observatory"},
    "brummbert_badge_day_23": {"day": 23, "route": "brummbert", "actor": None, "label": "Brummberts Rettungsplaketten-Tag", "preferredGifts": ["rescue_badge", "lamp_bulb", "warm_oil"], "location": "old_tunnel"},
    "mira_mapping_day_25": {"day": 25, "route": "mira", "actor": None, "label": "Miras erster Kartierungstag", "preferredGifts": ["river_stone", "folded_map", "star_map"], "location": "riverbed"},
    "sigi_birthday_9": {"day": 9, "route": None, "actor": "sigi", "label": "Sigi hat Geburtstag und Inventur", "preferredGifts": ["kiesel", "lamp_bulb"], "location": "garage"},
    "rosi_jubilee_14": {"day": 14, "route": None, "actor": "rosi", "label": "Rosis Markttag-Jubiläum", "preferredGifts": ["kiesel", "glass_charm"], "location": "scrapyard"},
    "kranhilde_inspection_19": {"day": 19, "route": None, "actor": "kranhilde", "label": "Kranhildes Abnahme", "preferredGifts": ["folded_map", "glass_charm"], "location": "hill_road"},
    "quiet_motors_24_special": {"day": 24, "route": None, "actor": "pumpi", "label": "Nacht der stillen Motoren", "preferredGifts": ["warm_oil", "lamp_bulb"], "location": "garage"},
}

CALENDAR = [
    {"id": "kalle_orientation_2", "day": 2, "period": "Morgen", "actor": "kalle", "label": "Bauhof-Einweisung", "location": "garage", "tags": ["social", "tutorial", "known-preferences"], "known": True},
    {"id": "rain_day_3", "day": 3, "period": "Abend", "label": "Regen am Wartungstor", "location": "rain_shelter", "tags": ["rain", "quiet"], "known": True},
    {"id": "scrap_market_4", "day": 4, "period": "Nachmittag", "actor": "sigi", "label": "Schrottmarkt oeffnet", "location": "scrapyard", "tags": ["technical", "shop", "social", "rumor"], "known": True},
    {"id": "tool_breakfast_5", "day": 5, "period": "Morgen", "actor": "kalle", "label": "Werkzeugfruehstueck", "location": "workshop", "tags": ["social", "group", "technical"], "known": True},
    {"id": "inspection_day_6", "day": 6, "period": "Morgen", "label": "TÜV-Frühstück", "location": "workshop", "tags": ["technical"], "known": True},
    {"id": "parts_delivery_7", "day": 7, "period": "Nachmittag", "actor": "rosi", "label": "Ersatzteil-Lieferung", "location": "workshop", "tags": ["technical", "shop", "gifts"], "known": True},
    {"id": "aurora_activation_8", "day": 8, "period": "Nacht", "route": "aurora", "label": "Aurora hat Spätschicht", "location": "observatory", "tags": ["stars", "memory"], "known": True},
    {"id": "sigi_inventory_9", "day": 9, "period": "Nachmittag", "actor": "sigi", "specialDay": "sigi_birthday_9", "label": "Sigi zaehlt Stapler und Kerzen", "location": "garage", "tags": ["social", "birthday", "rumor"], "known": True},
    {"id": "yard_grill_10", "day": 10, "period": "Abend", "label": "Bauhof-Grillen", "location": "garage", "tags": ["warm", "public"], "known": True},
    {"id": "roller_check_11", "day": 11, "period": "Nachmittag", "actor": "kalle", "label": "Walzenpruefung ohne neue Route", "location": "workshop", "tags": ["social", "technical", "reputation"], "known": True},
    {"id": "storm_rescue_12", "day": 12, "period": "Abend", "route": "brummbert", "label": "Sturm kommt auf", "location": "old_tunnel", "tags": ["rescue", "crisis"], "known": False, "repeatable": True},
    {"id": "lock_mood_13", "day": 13, "period": "Nacht", "label": "Seltsame Ruhe auf dem Hof", "location": "hill_road", "tags": ["quiet", "romantic"], "known": True},
    {"id": "rosi_jubilee_14", "day": 14, "period": "Nachmittag", "actor": "rosi", "specialDay": "rosi_jubilee_14", "label": "Rosis Markttag-Jubilaeum", "location": "scrapyard", "tags": ["shop", "social", "birthday", "gifts"], "known": True},
    {"id": "night_festival_15", "day": 15, "period": "Nacht", "label": "Jahrmarkt aufm Kiesplatz", "location": "festival", "tags": ["public", "romantic"], "known": True},
    {"id": "last_lock_16", "day": 16, "period": "Abend", "label": "Letzte klare Ansage", "location": "hill_road", "tags": ["romantic", "quiet"], "known": True},
    {"id": "sigi_rumor_17", "day": 17, "period": "Nachmittag", "actor": "sigi", "label": "Sigi hat was gehoert", "location": "garage", "tags": ["social", "rumor"], "known": True},
    {"id": "mira_map_18", "day": 18, "period": "Nachmittag", "route": "mira", "label": "Mira findet alte Karte", "location": "riverbed", "tags": ["water", "memory"], "known": False},
    {"id": "kranhilde_watch_19", "day": 19, "period": "Abend", "actor": "kranhilde", "specialDay": "kranhilde_inspection_19", "label": "Kranhilde sieht den ganzen Hof", "location": "hill_road", "tags": ["social", "public", "reputation"], "known": True},
    {"id": "hydraulic_warning_20", "day": 20, "period": "Abend", "label": "Hydraulikdruck-Warnung", "location": "workshop", "tags": ["technical", "crisis"], "known": True},
    {"id": "maintenance_day_21", "day": 21, "period": "Morgen", "actor": "kalle", "label": "Grosser Wartungstag", "location": "garage", "tags": ["technical", "warm", "group", "shop"], "known": True},
    {"id": "aurora_registration_22", "day": 22, "period": "Abend", "route": "aurora", "specialDay": "aurora_registration_22", "label": "Auroras Erstzulassung", "location": "observatory", "tags": ["birthday", "memory", "stars"], "known": True},
    {"id": "brummbert_badge_day_23", "day": 23, "period": "Nachmittag", "route": "brummbert", "specialDay": "brummbert_badge_day_23", "label": "Brummberts Rettungsplaketten-Tag", "location": "old_tunnel", "tags": ["birthday", "memory", "rescue"], "known": True},
    {"id": "quiet_motors_24", "day": 24, "period": "Nacht", "label": "Nacht der stillen Motoren", "location": "garage", "tags": ["quiet", "memory"], "known": True},
    {"id": "mira_mapping_day_25", "day": 25, "period": "Nachmittag", "route": "mira", "specialDay": "mira_mapping_day_25", "label": "Miras erster Kartierungstag", "location": "riverbed", "tags": ["birthday", "water", "memory"], "known": True},
    {"id": "yard_radio_26", "day": 26, "period": "Abend", "actor": "pumpi", "label": "Bauhof-Funkpruefung", "location": "workshop", "tags": ["social", "rumor", "crisis"], "known": True},
    {"id": "last_gift_27", "day": 27, "period": "Nachmittag", "label": "Letzte Runde beim Teilehaendler", "location": "scrapyard", "tags": ["shop", "memory"], "known": True},
    {"id": "farewell_grill_28", "day": 28, "period": "Abend", "actor": "kalle", "label": "Abschiedsgrillen", "location": "garage", "tags": ["social", "group", "public"], "known": True},
    {"id": "radio_silence_29", "day": 29, "period": "Nacht", "label": "Vorabend-Funkstille", "location": "hill_road", "tags": ["quiet", "finale"], "known": True},
    {"id": "confession_day_30", "day": 30, "period": "Nacht", "label": "Letzter Abend", "location": "hill_road", "tags": ["romantic", "finale"], "known": True},
]

ROUTE_PRESSURES = ["toward_romance", "toward_friendship", "needs_repair", "opens_secret", "toward_crisis", "toward_lockin"]


def cond(**kwargs):
    return kwargs


ROUTE_SPECS = {
    "aurora": [
        ("aurora_intro_puddle", "intro", "Prolog", "Aurora putzt ihre Kanzel, als der Spieler vorbeikommt. Sie tut so, als ob sie ihn nicht bemerkt hat.", "observatory", [], [], {"patience": 0}, ["kalter Kaffee in der Kanzel", "Ölfleck auf Beton"], ["aurora_first_seen"], {"toward_romance": 1, "toward_friendship": 1}),
        ("aurora_daily_lamp", "daily", "Immer dieselbe Schicht", "Wiederkehrende Szene: Aurora schraubt an irgendwas rum, damit sie nicht reden muss.", "garage", [], [], {}, ["verbeulter Schutzhelm", "Rost an der Kante"], [], {"toward_friendship": 1}),
        ("aurora_quiet_promise", "threshold", "Komm wieder", "Der Spieler verspricht, nach Feierabend wiederzukommen. Aurora zuckt nur mit der Schaufel.", "rain_shelter", [cond(stat="trust", gte=8)], [], {"patience": 4}, ["vergessener Lappen", "Kaffeemaschine summt"], ["aurora_quiet_promise"], {"toward_romance": 2, "opens_secret": 1}),
        ("aurora_star_map_date", "date", "Sternenkarte", "Aurora zeigt dem Spieler die alte Sternenkarte aus ihrer Kanzel. Sie weiss nicht, warum sie das tut.", "observatory", [cond(flag="aurora_quiet_promise")], [], {"charm": 6}, ["kalter Kaffee in der Kanzel", "Ölfleck auf Beton"], ["aurora_star_map_shared"], {"toward_romance": 2}),
        ("aurora_silent_shift", "friendship", "Nachtschicht", "Nachtschicht. Beide arbeiten nebeneinander her. Keiner sagt was — und das ist in Ordnung.", "garage", [], [], {"focus": 5}, ["Kaffeemaschine summt", "Rost an der Kante"], ["aurora_silent_friendship"], {"toward_friendship": 2}),
        ("aurora_left_behind", "crisis", "Abgehauen", "Aurora hat sich geöffnet, aber der Spieler musste plötzlich weg. Sie macht früh Feierabend.", "workshop", [cond(stat="bond", gte=18)], ["aurora_crisis_repaired"], {}, ["Ölfleck auf Beton", "Kaffeemaschine summt"], ["aurora_crisis_active"], {"toward_crisis": 3, "needs_repair": 2}),
        ("aurora_apology_lens", "repair", "Linse putzen", "Der Spieler putzt die alte Linse in der Sternwarte. Sagt nichts. Aurora beobachtet ihn von der Tür aus.", "observatory", [cond(flag="aurora_crisis_active"), cond(playerStat="patience", gte=12)], [], {"patience": 12}, ["Rost an der Kante", "vergessener Lappen"], ["aurora_crisis_repaired"], {"needs_repair": -2, "toward_romance": 2}),
        ("aurora_telescope_repair", "date", "Teleskop reparieren", "Das Teleskop hat einen Wackelkontakt. Sie schauen sich die Mechanik an. Aurora schaut mehr auf den Spieler als aufs Teleskop.", "observatory", [cond(playerStat="mechanics", gte=14)], [], {"mechanics": 14}, ["verbeulter Schutzhelm", "Ölfleck auf Beton"], ["aurora_telescope_repaired"], {"toward_romance": 2}),
        ("aurora_festival_distance", "daily", "Jahrmarkt", "Auf dem Jahrmarkt bleibt Aurora am Rand. Sie sagt, die Lichter seien 'ganz hübsch'. Das ist viel von ihr.", "festival", [cond(dayGte=15)], [], {}, ["kalter Kaffee in der Kanzel", "Rost an der Kante"], ["aurora_festival_seen"], {"toward_romance": 1, "toward_friendship": 1}),
        ("aurora_bucket_confession_hint", "romance", "Fast was gesagt", "Aurora stellt ihre Schaufel vor die Ausfahrt. Fragt, ob das hier auch morgen noch gilt.", "hill_road", [cond(stat="bond", gte=45), cond(flag="aurora_star_map_shared")], [], {"courage": 16}, ["Kaffeemaschine summt", "vergessener Lappen"], ["aurora_almost_confessed"], {"toward_lockin": 2, "toward_romance": 3}),
        ("aurora_friend_path_lamp", "friendship", "Kann auch so bleiben", "Aurora sagt: 'Man kann auch so bleiben. Ist auch okay.' Sie meint es ernst.", "garage", [cond(routePressure="toward_friendship", gte=3)], [], {}, ["verbeulter Schutzhelm", "Rost an der Kante"], ["aurora_friend_route_open"], {"toward_friendship": 3}),
        ("aurora_rain_return", "daily", "Regen", "Der Spieler kommt im Regen zurück — wie versprochen. Aurora sagt nichts, lässt aber die Kanzeltür auf.", "rain_shelter", [cond(flag="aurora_quiet_promise")], [], {"patience": 8}, ["Ölfleck auf Beton", "vergessener Lappen"], ["aurora_returned_in_rain"], {"opens_secret": 1}),
        ("aurora_glass_charm", "date", "Glas-Anhänger", "Der Glas-Anhänger hängt jetzt in der Kanzel. Aurora sagt, er reflektiert 'ganz gut'. Sieht ihn trotzdem die ganze Zeit an.", "observatory", [cond(flag="gift_glass_charm_aurora")], [], {}, ["kalter Kaffee in der Kanzel", "Kaffeemaschine summt"], ["aurora_glass_charm_kept"], {"toward_romance": 2}),
        ("aurora_map_fold", "threshold", "Alte Karte", "Aurora holt eine Karte raus, die sie seit Jahren nicht mehr aufgemacht hat. Faltet sie schnell wieder zusammen.", "observatory", [cond(stat="trust", gte=35)], [], {}, ["Ölfleck auf Beton", "verbeulter Schutzhelm"], ["aurora_private_map"], {"toward_romance": 2, "opens_secret": 1}),
        ("aurora_secret_crater", "secret", "Krater", "Hinter der Sternwarte ist ein Krater, den keiner kennt. Den zeigt sie nur, wer wirklich geblieben ist.", "observatory", [cond(flag="aurora_private_map"), cond(flag="aurora_returned_in_rain"), cond(stat="trust", gte=55), cond(routePressure="opens_secret", gte=3)], ["broken_promise_aurora"], {}, ["Rost an der Kante", "vergessener Lappen"], ["aurora_secret_open"], {"opens_secret": 4, "toward_romance": 3}),
        ("aurora_route_lock", "romance", "Bleibst du?", "Aurora will wissen, ob der Spieler wirklich bleibt — oder ob das alles nur 'bis zur nächsten Baustelle' ist.", "hill_road", [cond(stat="bond", gte=60), cond(flag="aurora_almost_confessed")], [], {}, ["kalter Kaffee in der Kanzel", "Kaffeemaschine summt"], ["route_lock_ready_aurora"], {"toward_lockin": 5}),
        ("aurora_normal_finale", "finale", "Morgen auch", "Szenenfinale: Unter der Treppe der Sternwarte. Kein grosses Drama, nur sie und der Spieler.", "observatory", [cond(stat="bond", gte=70), cond(flag="route_locked_aurora")], [], {}, ["verbeulter Schutzhelm", "Ölfleck auf Beton"], ["ending_candidate_normal_aurora"], {"toward_romance": 2}),
        ("aurora_true_finale", "finale", "Der erste Ort", "Finale: Der erste Ort, an dem sie sich gesehen haben. Jetzt spiegeln sich beide in derselben Pfütze.", "observatory", [cond(stat="bond", gte=88), cond(flag="aurora_crisis_repaired"), cond(flag="aurora_private_map"), cond(flag="route_locked_aurora")], [], {}, ["Rost an der Kante", "Kaffeemaschine summt"], ["ending_candidate_true_aurora"], {"toward_romance": 3}),
        ("aurora_friend_finale", "finale", "Licht brennt", "Freundschaftsende: Aurora lässt das Licht an, auch nach Feierabend. Für euch beide.", "garage", [cond(flag="aurora_friend_route_open")], [], {}, ["Kaffeemaschine summt", "verbeulter Schutzhelm"], ["ending_candidate_friend_aurora"], {"toward_friendship": 2}),
        ("aurora_missed_end_seed", "daily", "Licht aus", "Das Licht in der Kanzel ist aus. Aurora ist noch da, aber sie macht nicht auf.", "workshop", [cond(routePressure="needs_repair", gte=4)], [], {}, ["Ölfleck auf Beton", "kalter Kaffee in der Kanzel"], ["aurora_missed_seed"], {"needs_repair": 1}),
        ("aurora_secret_finale", "finale", "Kraterlicht", "Geheimes Ende: Der Krater hinter der Sternwarte. Er war nie auf dem Plan — aber er ist echt.", "observatory", [cond(flag="aurora_secret_open"), cond(stat="bond", gte=92), cond(flag="route_locked_aurora")], [], {}, ["vergessener Lappen", "Rost an der Kante"], ["ending_candidate_secret_aurora"], {"opens_secret": 5}),
    ],
    "brummbert": [
        ("brummbert_intro_lamp", "intro", "Prolog", "Brummbert sortiert alte Schrauben. Der Spieler kommt dazu. Brummbert sagt erstmal nichts.", "old_tunnel", [], [], {"courage": 0}, ["Kaffee aus der Thermoskanne", "dicke Arbeitshandschuhe"], ["brummbert_first_seen"], {"toward_romance": 1, "toward_friendship": 1}),
        ("brummbert_daily_gauge", "daily", "Druckmesser", "Wiederkehrend: Brummbert studiert den Druckmesser. Tut so, als ob ihn das mehr interessiert als der Spieler.", "workshop", [], [], {}, ["wummernder Diesel im Leerlauf", "Schrauben sortieren"], [], {"toward_friendship": 1}),
        ("brummbert_oil_compliment", "threshold", "War doch nichts", "Der Spieler sagt was Nettes. Brummbert weiss nicht wohin mit seinen Händen.", "garage", [cond(stat="warmth", gte=8)], [], {"charm": 4}, ["dicke Arbeitshandschuhe", "Kaffee aus der Thermoskanne"], ["brummbert_softness_seen"], {"toward_romance": 2}),
        ("brummbert_tunnel_walk", "date", "Langsam gehen", "Sie gehen durch den alten Tunnel. Brummbert passt sein Tempo an — ohne ein Wort.", "old_tunnel", [cond(playerStat="courage", gte=8)], [], {}, ["alte Narben im Blech", "wummernder Diesel im Leerlauf"], ["brummbert_tunnel_walk"], {"toward_romance": 2}),
        ("brummbert_friend_shift", "friendship", "Gutes Team", "Sie sind ein gutes Team auf dem Bauhof. Kein Datum, nur ehrliche Arbeit nebeneinander.", "workshop", [], [], {"mechanics": 5}, ["Schichtplan an der Pinnwand", "Schrauben sortieren"], ["brummbert_friendship_open"], {"toward_friendship": 2}),
        ("brummbert_storm_trigger", "crisis", "Sturm", "Ein Sturm kommt auf. Brummbert zuckt bei jedem Donner. Die alte Rettungssirene geht ihm nicht aus dem Kopf.", "old_tunnel", [cond(dayGte=12), cond(stat="trust", gte=18)], [], {"courage": 18}, ["wummernder Diesel im Leerlauf", "alte Narben im Blech"], ["brummbert_crisis_active"], {"toward_crisis": 3, "needs_repair": 2}),
        ("brummbert_after_storm", "repair", "Nach der Sirene", "Der Spieler bleibt, als der Sturm vorbei ist. Sagt nicht: 'Du warst stark.' Sagt nur: 'Ich bin da.'", "old_tunnel", [cond(flag="brummbert_crisis_active"), cond(playerStat="courage", gte=22)], [], {}, ["Kaffee aus der Thermoskanne", "dicke Arbeitshandschuhe"], ["brummbert_crisis_repaired"], {"needs_repair": -2, "toward_romance": 2}),
        ("brummbert_badge_gift", "date", "Plakette", "Brummbert kriegt seine alte Plakette zurück. Er dreht sich weg, damit der Spieler sein Gesicht nicht sieht.", "garage", [cond(flag="gift_rescue_badge_brummbert")], [], {}, ["alte Narben im Blech", "Schrauben sortieren"], ["brummbert_badge_kept"], {"toward_romance": 2, "opens_secret": 1}),
        ("brummbert_pressure_gauge", "threshold", "Zittern", "Der Druckmesser zeigt was an. Brummbert sagt, alles okay. Aber er zittert.", "workshop", [cond(stat="trust", gte=30), cond(playerStat="mechanics", gte=12)], [], {}, ["wummernder Diesel im Leerlauf", "Schichtplan an der Pinnwand"], ["brummbert_seen_under_pressure"], {"toward_romance": 2}),
        ("brummbert_festival_guard", "daily", "Abschirmen", "Auf dem Jahrmarkt stellt Brummbert sich zwischen den Spieler und die Menge. 'Da ist viel los', sagt er. Bleibt trotzdem.", "festival", [cond(dayGte=15)], [], {}, ["Kaffee aus der Thermoskanne", "dicke Arbeitshandschuhe"], ["brummbert_festival_guard"], {"toward_romance": 1, "toward_friendship": 1}),
        ("brummbert_soft_request", "romance", "Darf ich schwach sein?", "Brummbert fragt: 'Darf ich auch mal der sein, der nicht stark sein muss?'", "rain_shelter", [cond(stat="bond", gte=45), cond(flag="brummbert_softness_seen")], [], {"courage": 16}, ["alte Narben im Blech", "wummernder Diesel im Leerlauf"], ["brummbert_almost_confessed"], {"toward_lockin": 2, "toward_romance": 3}),
        ("brummbert_friend_finale_seed", "friendship", "Vertrauen", "Freundschaftsweg: Vertrauen ohne Besitzanspruch. Brummbert versteht das langsam.", "workshop", [cond(routePressure="toward_friendship", gte=3)], [], {}, ["Schrauben sortieren", "Schichtplan an der Pinnwand"], ["brummbert_friend_route_open"], {"toward_friendship": 3}),
        ("brummbert_lamp_bulb", "date", "Birne tauschen", "Eine Lampe wechseln. Klingt nach nichts, ist aber ihr kleines Ritual.", "old_tunnel", [cond(flag="gift_lamp_bulb_brummbert")], [], {}, ["dicke Arbeitshandschuhe", "wummernder Diesel im Leerlauf"], ["brummbert_lamp_replaced"], {"opens_secret": 1}),
        ("brummbert_no_mockery", "threshold", "Kein Spruch", "Brummbert hat einen Fehler gemacht. Wartet auf einen Spruch. Der kommt nicht.", "garage", [cond(stat="depth", gte=30)], [], {}, ["alte Narben im Blech", "Kaffee aus der Thermoskanne"], ["brummbert_softness_protected"], {"toward_romance": 2, "opens_secret": 1}),
        ("brummbert_secret_song", "secret", "Tunnel singt", "Der alte Tunnel summt, wenn der Wind richtig steht. Nur wer geblieben ist, hört das Lied.", "old_tunnel", [cond(flag="brummbert_crisis_repaired"), cond(flag="brummbert_badge_kept"), cond(routePressure="opens_secret", gte=3)], ["mocked_brummbert_softness"], {}, ["Schrauben sortieren", "Schichtplan an der Pinnwand"], ["brummbert_secret_open"], {"opens_secret": 4, "toward_romance": 3}),
        ("brummbert_route_lock", "romance", "Nicht mehr Wache schieben", "Brummbert fragt, ob er aufhören darf, Wache zu schieben. Ob der Spieler das auch will.", "hill_road", [cond(stat="bond", gte=60), cond(flag="brummbert_almost_confessed")], [], {}, ["wummernder Diesel im Leerlauf", "dicke Arbeitshandschuhe"], ["route_lock_ready_brummbert"], {"toward_lockin": 5}),
        ("brummbert_normal_finale", "finale", "Motor warm", "Finale: Neben dem noch warmen Motor. Keine Heldenstory, nur sie zwei.", "garage", [cond(stat="bond", gte=70), cond(flag="route_locked_brummbert")], [], {}, ["Kaffee aus der Thermoskanne", "Schrauben sortieren"], ["ending_candidate_normal_brummbert"], {"toward_romance": 2}),
        ("brummbert_true_finale", "finale", "Zurück im Tunnel", "Wahres Finale: Zurück im Tunnel. Keine Sirene mehr. Nur Stille und der Spieler.", "old_tunnel", [cond(stat="bond", gte=88), cond(flag="brummbert_crisis_repaired"), cond(flag="brummbert_softness_protected"), cond(flag="route_locked_brummbert")], [], {}, ["alte Narben im Blech", "dicke Arbeitshandschuhe"], ["ending_candidate_true_brummbert"], {"toward_romance": 3}),
        ("brummbert_friend_finale", "finale", "Ersatzlampe", "Freundschaftsende: Brummbert gibt dem Spieler die Ersatzlampe. 'Falls du mal eine brauchst.'", "workshop", [cond(flag="brummbert_friend_route_open")], [], {}, ["Schichtplan an der Pinnwand", "wummernder Diesel im Leerlauf"], ["ending_candidate_friend_brummbert"], {"toward_friendship": 2}),
        ("brummbert_missed_seed", "daily", "Tunnel kalt", "Der Tunnel ist leer. Brummbert ist da, aber seine Kanzel ist zu.", "old_tunnel", [cond(routePressure="needs_repair", gte=4)], [], {}, ["Kaffee aus der Thermoskanne", "alte Narben im Blech"], ["brummbert_missed_seed"], {"needs_repair": 1}),
        ("brummbert_secret_finale", "finale", "Tunnelgesang", "Geheimes Ende: Der Tunnel singt auch ohne Wind. Für die, die zugehört haben.", "old_tunnel", [cond(flag="brummbert_secret_open"), cond(stat="bond", gte=92), cond(flag="route_locked_brummbert")], [], {}, ["Schichtplan an der Pinnwand", "Schrauben sortieren"], ["ending_candidate_secret_brummbert"], {"opens_secret": 5}),
    ],
    "mira": [
        ("mira_intro_stone", "intro", "Prolog", "Mira sitzt am Bachlauf und macht sich Notizen. Der Spieler stört sie. Sie findet das... interessant.", "riverbed", [], [], {"focus": 0}, ["Notizblock voller Zahlen", "Bleistift am Ohr"], ["mira_first_seen"], {"toward_romance": 1, "toward_friendship": 1}),
        ("mira_daily_margin", "daily", "Notiz", "Wiederkehrend: Mira trägt was in ihre Karte ein. Sie erklärt nicht, was es bedeutet. Noch nicht.", "workshop", [], [], {}, ["Blaulicht-Piepser", "Karte mit Eselsohren"], [], {"toward_friendship": 1}),
        ("mira_first_map", "threshold", "Erste Karte", "Mira gibt dem Spieler eine Karte. Sie beobachtet, wie er sie aufschlägt — langsam oder schnell.", "riverbed", [cond(stat="trust", gte=8)], [], {"patience": 4}, ["Notizblock voller Zahlen", "zerknitterter Dienstplan"], ["mira_first_map_seen"], {"toward_romance": 2}),
        ("mira_river_stone_date", "date", "Stein mit Linie", "Der Flussstein hat eine helle Linie. Mira erklärt die Geologie. Aber sie behält den Stein.", "riverbed", [cond(flag="gift_river_stone_mira")], [], {}, ["Bleistift am Ohr", "nasse Stiefel am Heizungsrohr"], ["mira_river_stone_kept"], {"toward_romance": 2, "opens_secret": 1}),
        ("mira_map_friend", "friendship", "Zuhören", "Freundschaftsweg: Mira mag, dass der Spieler zuhört. Nicht versteht — nur zuhört.", "workshop", [], [], {"focus": 5}, ["Karte mit Eselsohren", "Notizblock voller Zahlen"], ["mira_friendship_open"], {"toward_friendship": 2}),
        ("mira_misread_clay", "crisis", "Falsch verstanden", "Der Spieler denkt, er versteht Mira. Aber er hat sie falsch gelesen. Sie zieht sich in Zahlen zurück.", "quarry_edge", [cond(stat="bond", gte=18)], ["mira_crisis_repaired"], {}, ["zerknitterter Dienstplan", "Bleistift am Ohr"], ["mira_crisis_active"], {"toward_crisis": 3, "needs_repair": 2}),
        ("mira_repair_sediment", "repair", "Eingestehen", "Der Spieler sagt: 'Ich hab nicht kapiert, was du meintest.' Mira nickt. Das reicht.", "riverbed", [cond(flag="mira_crisis_active"), cond(playerStat="focus", gte=14)], [], {}, ["nasse Stiefel am Heizungsrohr", "Karte mit Eselsohren"], ["mira_crisis_repaired"], {"needs_repair": -2, "toward_romance": 2}),
        ("mira_forgotten_map", "threshold", "Alte Karte", "Mira findet eine alte Grundwasserkarte. Da ist was eingezeichnet, das nicht da sein dürfte.", "riverbed", [cond(dayGte=18), cond(stat="depth", gte=22)], [], {}, ["Blaulicht-Piepser", "zerknitterter Dienstplan"], ["mira_forgotten_map"], {"opens_secret": 2}),
        ("mira_clay_poem", "date", "Im Lehm", "Mira schreibt was in den feuchten Lehm. Sie sagt nicht, was es ist. Aber sie lässt es stehen.", "quarry_edge", [cond(playerStat="focus", gte=12)], [], {}, ["Bleistift am Ohr", "nasse Stiefel am Heizungsrohr"], ["mira_clay_poem_seen"], {"toward_romance": 2}),
        ("mira_festival_edges", "daily", "Schatten zählen", "Auf dem Jahrmarkt zählt Mira die Schatten. Die Lichter sind zu laut für sie.", "festival", [cond(dayGte=15)], [], {}, ["Notizblock voller Zahlen", "Karte mit Eselsohren"], ["mira_festival_seen"], {"toward_friendship": 1, "toward_romance": 1}),
        ("mira_exact_listening", "romance", "Ohne zu vereinfachen", "Mira fragt: 'Kannst du mich mögen, ohne mich einfacher zu machen, als ich bin?'", "rain_shelter", [cond(stat="bond", gte=45), cond(flag="mira_first_map_seen")], [], {"focus": 16}, ["Notizblock voller Zahlen", "Blaulicht-Piepser"], ["mira_almost_confessed"], {"toward_lockin": 2, "toward_romance": 3}),
        ("mira_friend_finale_seed", "friendship", "Karte ohne Ziel", "Freundschaft ist für Mira eine Karte ohne Ziel. Sie zeigt dem Spieler, dass das okay ist.", "workshop", [cond(routePressure="toward_friendship", gte=3)], [], {}, ["Karte mit Eselsohren", "zerknitterter Dienstplan"], ["mira_friend_route_open"], {"toward_friendship": 3}),
        ("mira_folded_map_gift", "date", "Karte geschenkt", "Mira nimmt die Karte an. Sie wartet, ob der Spieler fragt, was sie bedeutet. Er fragt nicht.", "riverbed", [cond(flag="gift_folded_map_mira")], [], {}, ["Bleistift am Ohr", "nasse Stiefel am Heizungsrohr"], ["mira_folded_map_kept"], {"opens_secret": 1}),
        ("mira_depth_measure", "threshold", "Tiefe messen", "Mira misst die Tiefe einer Pfütze. Dann fragt sie: 'Was kann man nicht messen?'", "quarry_edge", [cond(stat="depth", gte=40)], [], {}, ["Notizblock voller Zahlen", "Blaulicht-Piepser"], ["mira_depth_question"], {"toward_romance": 2, "opens_secret": 1}),
        ("mira_secret_spring", "secret", "Quelle", "Die Quelle unter dem Steinbruch. Nur wer genau war und geblieben ist, findet sie.", "quarry_edge", [cond(flag="mira_river_stone_kept"), cond(flag="mira_forgotten_map"), cond(flag="mira_crisis_repaired"), cond(routePressure="opens_secret", gte=3)], [], {}, ["Blaulicht-Piepser", "Karte mit Eselsohren"], ["mira_secret_open"], {"opens_secret": 4, "toward_romance": 3}),
        ("mira_route_lock", "romance", "Unbekannter Weg", "Mira will wissen: 'Wählst du den Weg, der auf keiner Karte steht?'", "hill_road", [cond(stat="bond", gte=60), cond(flag="mira_almost_confessed")], [], {}, ["Notizblock voller Zahlen", "zerknitterter Dienstplan"], ["route_lock_ready_mira"], {"toward_lockin": 5}),
        ("mira_normal_finale", "finale", "Kartenrand", "Finale: Am Rand einer Grundwasserkarte steht mehr als nur Daten.", "riverbed", [cond(stat="bond", gte=70), cond(flag="route_locked_mira")], [], {}, ["Bleistift am Ohr", "nasse Stiefel am Heizungsrohr"], ["ending_candidate_normal_mira"], {"toward_romance": 2}),
        ("mira_true_finale", "finale", "Wasser unter Stein", "Wahres Finale: Da, wo der erste Stein lag, ist jetzt Wasser. Mira sagt: 'Das war schon immer da.'", "riverbed", [cond(stat="bond", gte=88), cond(flag="mira_crisis_repaired"), cond(flag="mira_depth_question"), cond(flag="route_locked_mira")], [], {}, ["Karte mit Eselsohren", "Blaulicht-Piepser"], ["ending_candidate_true_mira"], {"toward_romance": 3}),
        ("mira_friend_finale", "finale", "Platz im Atlas", "Freundschaftsende: Miras neue Karten haben immer eine Ecke für den Spieler.", "workshop", [cond(flag="mira_friend_route_open")], [], {}, ["zerknitterter Dienstplan", "Notizblock voller Zahlen"], ["ending_candidate_friend_mira"], {"toward_friendship": 2}),
        ("mira_missed_seed", "daily", "Keine Markierung", "Die Karte hat keine Markierung. Mira ist da, aber sie zeichnet nichts ein.", "workshop", [cond(routePressure="needs_repair", gte=4)], [], {}, ["Bleistift am Ohr", "nasse Stiefel am Heizungsrohr"], ["mira_missed_seed"], {"needs_repair": 1}),
        ("mira_secret_finale", "finale", "Singender Steinbruch", "Geheimes Ende: Der Boden des Steinbruchs singt. Wasser von ganz unten.", "quarry_edge", [cond(flag="mira_secret_open"), cond(stat="bond", gte=92), cond(flag="route_locked_mira")], [], {}, ["Blaulicht-Piepser", "zerknitterter Dienstplan"], ["ending_candidate_secret_mira"], {"opens_secret": 5}),
    ],
}


CATEGORY_PERIODS = {
    "intro": ["Morgen", "Nachmittag", "Abend", "Nacht"],
    "daily": ["Morgen", "Nachmittag", "Abend", "Nacht"],
    "date": ["Nachmittag", "Abend"],
    "threshold": ["Abend", "Nacht"],
    "romance": ["Abend", "Nacht"],
    "crisis": ["Morgen", "Nachmittag", "Abend", "Nacht"],
    "repair": ["Morgen", "Nachmittag"],
    "friendship": ["Morgen", "Nachmittag", "Abend"],
    "secret": ["Nacht"],
    "finale": ["Nacht"],
}


def make_node(route, spec):
    (node_id, category, chapter, premise, location, required, blocked, stat_hints, motifs, flags, pressure) = spec
    return {
        "id": node_id,
        "route": route,
        "category": category,
        "chapter": chapter,
        "premise": premise,
        "location": location,
        "periodAffinity": CATEGORY_PERIODS.get(category, ["Morgen", "Nachmittag", "Abend", "Nacht"]),
        "requiredFlags": required,
        "blockedByFlags": blocked,
        "statHints": stat_hints,
        "motifs": motifs,
        "choiceSet": category,
        "nextCandidates": [],
        "routePressureEffects": pressure,
        "setsFlags": flags,
        "translationStyleNotes": STYLE_BIBLE["routes"][route],
    }


ROUTES = {route: [make_node(route, spec) for spec in specs] for route, specs in ROUTE_SPECS.items()}

FLAG_REGISTRY = sorted({
    flag
    for nodes in ROUTES.values()
    for node in nodes
    for flag in node.get("setsFlags", [])
} | {
    flag
    for nodes in ROUTES.values()
    for node in nodes
    for flag in node.get("blockedByFlags", [])
} | {
    f"route_locked_{route}" for route in BAGGERS
} | {
    f"broken_promise_{route}" for route in BAGGERS
} | {
    f"active_promise_{route}" for route in BAGGERS
} | {
    f"gift_{item}_{route}" for route in BAGGERS for item in ITEMS
} | {
    f"missed_festival_{route}" for route in BAGGERS
} | {
    f"missed_route_{route}" for route in BAGGERS
} | {
    f"missed_{event['id']}" for event in CALENDAR
} | {
    f"event_{event['id']}" for event in CALENDAR
} | {
    f"special_day_{sid}" for sid in SPECIAL_DAYS
})

ENDINGS = {
    route: {
        "bad": {"label": "Bad End", "priority": 10},
        "missed": {"label": "Missed Route End", "priority": 20},
        "friendship": {"label": "Friendship End", "priority": 30},
        "normal": {"label": "Normal Romance End", "priority": 40},
        "true": {"label": "True Romance End", "priority": 50},
        "secret": {"label": "Secret End", "priority": 60},
    } for route in BAGGERS
}


CHOICE_SETS = {
    "default": [
        {"id": "sincere", "label": "Ehrlich sagen", "message": "Ich will nichts beschönigen. Ich bin einfach gern hier."},
        {"id": "careful", "label": "Raum lassen", "message": "Sag einfach, wenn ich zu nah komm. Ich warts ab."},
        {"id": "bold", "label": "Klipp und klar", "message": "Ich weiss nicht, ob das grad richtig ist. Aber ich will, dass du weisst: Du bist mir wichtig."},
    ],
    "crisis": [
        {"id": "stay", "label": "Bleiben", "message": "Ich geh nicht. Auch wenn du jetzt lieber allein wärst."},
        {"id": "gentle", "label": "Leise fragen", "message": "Ich muss nicht wissen, was los ist. Ich bin da."},
        {"id": "space", "label": "Rückzug", "message": "Ich wart draussen. Nicht weil ich abhaue, sondern damit du Luft kriegst."},
    ],
    "repair": [
        {"id": "apologize", "label": "Entschuldigen", "message": "Hab nicht richtig hingesehen. Tut mir leid."},
        {"id": "explain", "label": "Erklären", "message": "Ich will dir sagen, warum ich das gemacht hab — nicht als Ausrede, sondern damit du's verstehst."},
        {"id": "action", "label": "Zeigen, nicht sagen", "message": "Lass mich's dir zeigen. Worte reichen grad nicht."},
    ],
    "date": [
        {"id": "compliment", "label": "Was Nettes sagen", "message": "Du siehst gut aus heute. Wollte ich nur mal sagen."},
        {"id": "question", "label": "Fragen", "message": "Woran hast du grad gedacht? Musst nicht antworten, aber ich würd's gern wissen."},
        {"id": "silence", "label": "Nichts sagen", "message": "Ich will nix sagen. Nur hier sein."},
    ],
    "threshold": [
        {"id": "approach", "label": "Näher kommen", "message": "Ich will dir näher sein. Nicht zu schnell, aber ich will, dass du's weisst."},
        {"id": "wait", "label": "Abwarten", "message": "Ich wart. Du bestimmst."},
        {"id": "promise", "label": "Versprechen", "message": "Ich versprech nur, was ich halten kann. Und ich versprech: Ich komm wieder."},
    ],
    "romance": [
        {"id": "confess", "label": "Andeuten", "message": "Du wirst mir wichtig. Ich will nicht, dass das kaputtgeht."},
        {"id": "protect", "label": "Abfangen", "message": "Du musst nicht stark sein, wenn ich da bin."},
        {"id": "choose", "label": "Wählen", "message": "Ich wähl dich. Nicht aus Einsamkeit. Sondern weil du echt bist."},
    ],
    "friendship": [
        {"id": "steady", "label": "Beständigkeit", "message": "Du bist mir wichtig. Nicht als Ziel, sondern als einer, der bleibt."},
        {"id": "light", "label": "Leicht bleiben", "message": "Lass uns nicht alles schwer machen. Ich bin gern in deiner Nähe."},
        {"id": "trust", "label": "Vertrauen", "message": "Ich vertrau dir. Das kommt nicht oft vor."},
    ],
    "finale": [
        {"id": "stay_end", "label": "Bleiben", "message": "Ich will, dass das hier nicht aufhört."},
        {"id": "promise_end", "label": "Versprechen", "message": "Egal was kommt — ich komm zurück."},
        {"id": "silence_end", "label": "Nur da sein", "message": "Manche Dinge brauchen keine Worte."},
    ],
    "secret": [
        {"id": "trust_secret", "label": "Vertrauen", "message": "Ich hab keine Angst davor, was du mir zeigst."},
        {"id": "reciprocate", "label": "Erwidern", "message": "Du zeigst mir was von dir. Dann zeig ich dir was von mir."},
        {"id": "witness", "label": "Nur zusehen", "message": "Ich muss nichts zurückgeben. Ich will nur sehen, was du mir zeigen willst."},
    ],
    "intro": [
        {"id": "sincere", "label": "Ehrlich sagen", "message": "Ich will nichts beschönigen. Ich bin einfach gern hier."},
        {"id": "careful", "label": "Raum lassen", "message": "Sag einfach, wenn ich zu nah komm. Ich warts ab."},
        {"id": "bold", "label": "Klipp und klar", "message": "Ich weiss nicht, ob das grad richtig ist. Aber ich will, dass du weisst: Du bist mir wichtig."},
    ],
    "daily": [
        {"id": "work_together", "label": "Helfen", "message": "Lass mich anpacken. Nicht aus Pflicht, sondern weil ich Bock hab."},
        {"id": "observe", "label": "Zusehen", "message": "Ich schau dir gern zu. Du musst nix dafür tun."},
        {"id": "talk", "label": "Quatschen", "message": "Erzähl mir von deinem Tag. Auch die kleinen Sachen."},
    ],
}


def public_game_data():
    return {
        "styleBible": STYLE_BIBLE,
        "baggers": BAGGERS,
        "locations": LOCATIONS,
        "items": ITEMS,
        "giftPreferences": GIFT_PREFERENCES,
        "scheduleActions": SCHEDULE_ACTIONS,
        "socialActors": SOCIAL_ACTORS,
        "socialRelations": SOCIAL_RELATIONS,
        "specialDays": SPECIAL_DAYS,
        "reputationKeys": REPUTATION_KEYS,
        "playerStyles": PLAYER_STYLES,
        "calendar": CALENDAR,
        "routes": ROUTES,
        "flagRegistry": FLAG_REGISTRY,
        "routePressures": ROUTE_PRESSURES,
        "endings": ENDINGS,
        "choiceSets": CHOICE_SETS,
    }
