#!/usr/bin/env python3
"""Build a PLS pronunciation dictionary for classical Latin.

Uses CLTK's Allen reconstruction (W. Sidney Allen, Vox Latina) to generate
IPA transcriptions for a core Latin vocabulary, then writes a W3C PLS file
that ElevenLabs accepts via its pronunciation dictionary API.

Covers ~600 high-frequency words + proper nouns from standard texts.
Pass --word-list to extend with your own vocabulary file (one word per line).
"""

import argparse
import sys
from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ET


# Manually curated proper nouns — CLTK's transcriber handles inflected forms
# but not proper names reliably. IPA follows Allen's Vox Latina conventions.
PROPER_NOUNS: dict[str, str] = {
    "Caesar": "ˈkae̯.sar",
    "caesar": "ˈkae̯.sar",
    "Cicero": "ˈki.ke.roː",
    "cicero": "ˈki.ke.roː",
    "Roma": "ˈroː.ma",
    "Gallia": "ˈɡal.li.a",
    "Galli": "ˈɡal.liː",
    "Gallus": "ˈɡal.lus",
    "Italia": "iˈta.li.a",
    "Graecia": "ˈɡrae̯.ki.a",
    "Hispania": "hisˈpaː.ni.a",
    "Germania": "ɡerˈmaː.ni.a",
    "Britannia": "briˈtan.ni.a",
    "Vergilius": "werˈɡi.li.us",
    "Horatius": "hoˈraː.ti.us",
    "Livius": "ˈliː.wi.us",
    "Tacitus": "ˈta.ki.tus",
    "Seneca": "ˈse.ne.ka",
    "Plautus": "ˈplau̯.tus",
    "Terentius": "teˈren.ti.us",
    "Ovidius": "oˈwiː.di.us",
    "Marcus": "ˈmar.kus",
    "Gaius": "ˈɡae̯.i.us",
    "Lucius": "ˈluː.ki.us",
    "Titus": "ˈtiː.tus",
    "Publius": "ˈpuː.bli.us",
    "Quintus": "ˈkwin.tus",
    "Gnaeus": "ˈɡnae̯.us",
    "Aeneas": "ae̯ˈneː.as",
    "Troia": "ˈtroj.ja",
    "Carthago": "karˈthaː.ɡoː",
    "Pompeius": "pomˈpej.jus",
    "Antonius": "anˈtoː.ni.us",
    "Brutus": "ˈbruː.tus",
    "Augustus": "au̯ˈɡus.tus",
    "Romulus": "ˈroː.mu.lus",
    "Remus": "ˈreː.mus",
    "Iulius": "ˈjuː.li.us",
    "Iulia": "ˈjuː.li.a",
    # Familia Romana characters
    "Medus": "ˈmeː.dus",
    "Lydia": "ˈly.di.a",
    "Davus": "ˈdaː.wus",
    "Syrus": "ˈsy.rus",
    # Common geographic
    "Rhenus": "ˈreː.nus",
    "Danuvius": "daˈnuː.wi.us",
    "Padus": "ˈpaː.dus",
    "Rubicon": "ˈru.bi.koːn",
    "Alpes": "ˈal.peːs",
    "Apenninus": "a.penˈniː.nus",
    "Sicilia": "siˈki.li.a",
    "Aegyptus": "ae̯ˈɡyp.tus",
    "Athena": "aˈtʰeː.nae̯",
    "Athenae": "aˈtʰeː.nae̯",
}


# Core Latin vocabulary — drawn from frequency lists for Caesar, Cicero,
# Vergil, Ovid, Livy, and the Familia Romana textbook series.
CORE_LATIN_WORDS: list[str] = [
    # Personal pronouns & demonstratives
    "ego", "tu", "nos", "vos",
    "is", "ea", "id", "ei", "eam", "eum", "eos", "eas",
    "hic", "haec", "hoc", "huic", "hunc", "hanc", "hos", "has",
    "ille", "illa", "illud", "illius", "illi", "illum", "illam", "illos", "illas",
    "iste", "ista", "istud",
    "ipse", "ipsa", "ipsum",
    "idem", "eadem",
    "qui", "quae", "quod", "cuius", "cui", "quem", "quam", "quos", "quas", "quibus",
    "quis", "quid",
    "se", "sui", "sibi", "sese",
    # esse (to be)
    "sum", "es", "est", "sumus", "estis", "sunt",
    "eram", "eras", "erat", "eramus", "eratis", "erant",
    "ero", "eris", "erit", "erimus", "eritis", "erunt",
    "esse", "fuisse", "fore",
    "fui", "fuisti", "fuit", "fuimus", "fuistis", "fuerunt",
    "sim", "sis", "sit", "simus", "sitis", "sint",
    "essem", "esses", "esset", "essemus", "essetis", "essent",
    # facio
    "facio", "facis", "facit", "facimus", "facitis", "faciunt",
    "facere", "feci", "factum", "factus", "facta",
    "fac", "facite",
    # dico
    "dico", "dicis", "dicit", "dicimus", "dicitis", "dicunt",
    "dicere", "dixi", "dictum", "dictus",
    "dic", "dicite",
    # video
    "video", "vides", "videt", "videmus", "videtis", "vident",
    "videre", "vidi", "visum", "visus",
    # volo / nolo / malo
    "volo", "vis", "vult", "volumus", "vultis", "volunt", "velle", "volui",
    "nolo", "nolunt", "nolle", "nolui", "noli", "nolite",
    "malo", "mavis", "mavult", "malumus", "mavultis", "malunt", "malle", "malui",
    # possum
    "possum", "potes", "potest", "possumus", "potestis", "possunt",
    "posse", "potui", "potuerit",
    # venio
    "venio", "venis", "venit", "venimus", "venitis", "veniunt",
    "venire", "ventum",
    # eo
    "eo", "it", "imus", "itis", "eunt", "ire", "ivi", "itum",
    "ibam", "ibas", "ibat", "ibamus", "ibatis", "ibant",
    "ibo", "ibis", "ibit", "ibimus", "ibitis", "ibunt",
    # do
    "do", "das", "dat", "damus", "datis", "dant",
    "dare", "dedi", "datum", "da", "date",
    # habeo
    "habeo", "habes", "habet", "habemus", "habetis", "habent",
    "habere", "habui", "habitum",
    # duco
    "duco", "ducis", "ducit", "ducimus", "ducitis", "ducunt",
    "ducere", "duxi", "ductum", "duc", "ducite",
    # mitto
    "mitto", "mittis", "mittit", "mittimus", "mittitis", "mittunt",
    "mittere", "misi", "missum",
    # fero
    "fero", "fers", "fert", "ferimus", "fertis", "ferunt",
    "ferre", "tuli", "latum", "fer", "ferte",
    # capio
    "capio", "capis", "capit", "capimus", "capitis", "capiunt",
    "capere", "cepi", "captum",
    # ago
    "ago", "agis", "agit", "agimus", "agitis", "agunt",
    "agere", "egi", "actum", "age", "agite",
    # audio
    "audio", "audis", "audit", "audimus", "auditis", "audiunt",
    "audire", "audivi", "auditum", "audi", "audite",
    # scribo
    "scribo", "scribis", "scribit", "scribimus", "scribitis", "scribunt",
    "scribere", "scripsi", "scriptum",
    # lego
    "lego", "legis", "legit", "legimus", "legitis", "legunt",
    "legere", "legi", "lectum",
    # pono
    "pono", "ponis", "ponit", "ponimus", "ponitis", "ponunt",
    "ponere", "posui", "positum",
    # moveo
    "moveo", "moves", "movet", "movemus", "movetis", "movent",
    "movere", "movi", "motum",
    # maneo
    "maneo", "manes", "manet", "manemus", "manetis", "manent",
    "manere", "mansi", "mansum",
    # iubeo
    "iubeo", "iubes", "iubet", "iubemus", "iubetis", "iubent",
    "iubere", "iussi", "iussum",
    # cognosco
    "cognosco", "cognoscis", "cognoscit", "cognoscimus", "cognoscitis", "cognoscunt",
    "cognoscere", "cognovi", "cognitum",
    # relinquo
    "relinquo", "relinquis", "relinquit", "relinquimus", "relinquitis", "relinquunt",
    "relinquere", "reliqui", "relictum",
    # interficio / occido
    "interficio", "interficis", "interficit", "interficere", "interfeci", "interfectum",
    "occido", "occidis", "occidit", "occidere", "occidi", "occisum",
    # accipio
    "accipio", "accipis", "accipit", "accipere", "accepi", "acceptum",
    # timeo / debeo
    "timeo", "times", "timet", "timemus", "timetis", "timent", "timere", "timui",
    "debeo", "debes", "debet", "debemus", "debetis", "debent", "debere", "debui", "debitum",
    # Other high-frequency verbs
    "puto", "putas", "putat", "putamus", "putatis", "putant", "putare", "putavi",
    "peto", "petis", "petit", "petimus", "petitis", "petunt", "petere", "petivi", "petitum",
    "quaero", "quaeris", "quaerit", "quaerimus", "quaeritis", "quaerunt", "quaerere", "quaesivi", "quaesitum",
    "respondeo", "respondes", "respondet", "respondere", "respondi", "responsum",
    "narro", "narras", "narrat", "narrare", "narravi",
    "intro", "intras", "intrat", "intrare", "intravi",
    "exeo", "exis", "exit", "eximus", "exitis", "exeunt", "exire", "exivi",
    "cedo", "cedis", "cedit", "cedimus", "ceditis", "cedunt", "cedere", "cessi",
    "curro", "curris", "currit", "currimus", "curritis", "currunt", "currere", "cucurri",
    "porto", "portas", "portat", "portamus", "portatis", "portant", "portare", "portavi", "portatum",
    "specto", "spectas", "spectat", "spectamus", "spectatis", "spectant", "spectare", "spectavi",
    "sto", "stas", "stat", "stamus", "statis", "stant", "stare", "steti",
    "sedeo", "sedes", "sedet", "sedemus", "sedetis", "sedent", "sedere", "sedi",
    "dormio", "dormis", "dormit", "dormimus", "dormitis", "dormiunt", "dormire", "dormivi",
    "canto", "cantas", "cantat", "cantamus", "cantatis", "cantant", "cantare", "cantavi",
    "rideo", "rides", "ridet", "ridemus", "ridetis", "rident", "ridere", "risi",
    "ploro", "ploras", "plorat", "ploramus", "ploratis", "plorant", "plorare",
    "laudo", "laudas", "laudat", "laudamus", "laudatis", "laudant", "laudare", "laudavi",
    "amo", "amas", "amat", "amamus", "amatis", "amant", "amare", "amavi", "amatum",
    "vivo", "vivis", "vivit", "vivimus", "vivitis", "vivunt", "vivere", "vixi",
    "cado", "cadis", "cadit", "cadimus", "caditis", "cadunt", "cadere", "cecidi",
    "vinco", "vincis", "vincit", "vincimus", "vincitis", "vincunt", "vincere", "vici", "victum",
    # Nouns — 1st declension
    "via", "viae", "viam", "vias", "viis",
    "terra", "terrae", "terram", "terras", "terris",
    "aqua", "aquae", "aquam", "aquas",
    "silva", "silvae", "silvam", "silvas", "silvis",
    "porta", "portae", "portam", "portas", "portis",
    "casa", "casae", "casam", "casas",
    "familia", "familiae", "familiam", "familias", "familiis",
    "puella", "puellae", "puellam", "puellas", "puellis",
    "femina", "feminae", "feminam", "feminas", "feminis",
    "lingua", "linguae", "linguam", "linguas", "linguis",
    "fabula", "fabulae", "fabulam", "fabulas", "fabulis",
    "schola", "scholae", "scholam", "scholas", "scholis",
    "vita", "vitae", "vitam", "vitas",
    "natura", "naturae", "naturam",
    "gloria", "gloriae", "gloriam",
    "fuga", "fugae", "fugam",
    "cura", "curae", "curam", "curas",
    "hora", "horae", "horam", "horas", "horis",
    "luna", "lunae", "lunam",
    "stella", "stellae", "stellam", "stellas",
    "herba", "herbae", "herbam", "herbas",
    "nauta", "nautae", "nautam", "nautas",
    "agricola", "agricolae", "agricolam",
    "poeta", "poetae", "poetam",
    # Nouns — 2nd declension
    "dominus", "domini", "dominum", "dominos", "dominorum", "dominis",
    "servus", "servi", "servum", "servos", "servorum", "servis",
    "amicus", "amici", "amicum", "amicos", "amicorum", "amicis",
    "discipulus", "discipuli", "discipulum", "discipulos",
    "magister", "magistri", "magistrum", "magistros",
    "filius", "filii", "filium", "filios", "filiorum", "filiis",
    "puer", "pueri", "puerum", "pueros", "puerorum", "pueris",
    "vir", "viri", "virum", "viros", "virorum", "viris",
    "animus", "animi", "animum", "animos",
    "deus", "dei", "deum", "deos", "deorum",
    "locus", "loci", "locum", "locos", "locorum", "locis",
    "liber", "libri", "librum", "libros", "librorum", "libris",
    "numerus", "numeri", "numerum", "numeros",
    "populus", "populi", "populum", "populos",
    "annus", "anni", "annum", "annos", "annorum", "annis",
    "campus", "campi", "campum", "campos",
    "murus", "muri", "murum", "muros",
    "equus", "equi", "equum", "equos",
    "gladius", "gladii", "gladium", "gladios",
    "oculus", "oculi", "oculum", "oculos",
    "digitus", "digiti", "digitum", "digitos",
    "verbum", "verbi", "verba", "verborum", "verbis",
    "bellum", "belli", "bella", "bellorum", "bellis",
    "imperium", "imperii", "imperia",
    "caelum", "caeli",
    "periculum", "periculi", "pericula",
    "oppidum", "oppidi", "oppida", "oppidorum",
    "proelium", "proelii", "proelia",
    "praemium", "praemii", "praemia",
    "auxilium", "auxilii", "auxilia",
    "studium", "studii", "studia",
    "gaudium", "gaudii", "gaudia",
    "odium", "odii",
    "otium", "otii",
    "negotium", "negotii",
    # Nouns — 3rd declension
    "homo", "hominis", "hominem", "homines", "hominum", "hominibus",
    "rex", "regis", "regem", "reges", "regum", "regibus",
    "pater", "patris", "patrem", "patres", "patrum", "patribus",
    "mater", "matris", "matrem", "matres", "matrum", "matribus",
    "frater", "fratris", "fratrem", "fratres", "fratrum", "fratribus",
    "soror", "sororis", "sororem", "sorores", "sororum", "sororibus",
    "mons", "montis", "montem", "montes", "montium", "montibus",
    "urbs", "urbis", "urbem", "urbes", "urbium", "urbibus",
    "nox", "noctis", "noctem", "noctes", "noctium", "noctibus",
    "lux", "lucis", "lucem", "luces", "lucibus",
    "vox", "vocis", "vocem", "voces", "vocum", "vocibus",
    "pax", "pacis", "pacem",
    "lex", "legis", "legem", "leges", "legum", "legibus",
    "dux", "ducis", "ducem", "duces", "ducum", "ducibus",
    "miles", "militis", "militem", "milites", "militum", "militibus",
    "consul", "consulis", "consulem", "consules", "consulibus",
    "imperator", "imperatoris", "imperatorem", "imperatores",
    "mors", "mortis", "mortem",
    "pars", "partis", "partem", "partes", "partium", "partibus",
    "caput", "capitis", "capita", "capitum", "capitibus",
    "corpus", "corporis", "corpora", "corporum", "corporibus",
    "tempus", "temporis", "tempora", "temporum", "temporibus",
    "nomen", "nominis", "nomina", "nominum", "nominibus",
    "flumen", "fluminis", "flumina", "fluminum", "fluminibus",
    "carmen", "carminis", "carmina",
    "iter", "itineris", "itinera",
    "hostis", "hostis", "hostem", "hostes", "hostium", "hostibus",
    "navis", "navis", "navem", "naves", "navium", "navibus",
    "civis", "civis", "civem", "cives", "civium", "civibus",
    "finis", "finis", "finem", "fines", "finium", "finibus",
    "ignis", "ignis", "ignem", "ignes", "ignium", "ignibus",
    "mens", "mentis", "mentem", "mentes", "mentium", "mentibus",
    "gens", "gentis", "gentem", "gentes", "gentium", "gentibus",
    "pons", "pontis", "pontem", "pontes", "pontium", "pontibus",
    "amor", "amoris", "amorem", "amores", "amorum", "amoribus",
    "dolor", "doloris", "dolorem", "dolores",
    "honor", "honoris", "honorem", "honores",
    "labor", "laboris", "laborem", "labores",
    "timor", "timoris", "timorem", "timores",
    "terror", "terroris", "terrorem", "terrores",
    "virtus", "virtutis", "virtutem", "virtutes", "virtutum",
    "civitas", "civitatis", "civitatem", "civitates",
    "libertas", "libertatis", "libertatem",
    "veritas", "veritatis", "veritatem",
    "voluntas", "voluntatis", "voluntatem",
    "potestas", "potestatis", "potestatem",
    "senatus", "senatui", "senatum",
    "exercitus", "exercitui", "exercitum",
    "manus", "manui", "manum", "manibus",
    "dies", "diei", "diem", "diebus",
    "res", "rei", "rem", "rebus",
    "fides", "fidei", "fidem",
    "spes", "spei", "spem",
    # Adjectives — 1st / 2nd declension
    "magnus", "magna", "magnum", "magni", "magnae",
    "parvus", "parva", "parvum",
    "bonus", "bona", "bonum", "boni", "bonae",
    "malus", "mala", "malum",
    "longus", "longa", "longum",
    "altus", "alta", "altum",
    "latus", "lata", "latum",
    "novus", "nova", "novum",
    "antiquus", "antiqua", "antiquum",
    "primus", "prima", "primum",
    "secundus", "secunda", "secundum",
    "tertius", "tertia", "tertium",
    "multus", "multa", "multum", "multi", "multae",
    "pauci", "paucae", "pauca",
    "omnis", "omne", "omnes", "omnia", "omnibus",
    "alius", "alia", "aliud",
    "alter", "altera", "alterum",
    "nullus", "nulla", "nullum",
    "solus", "sola", "solum",
    "totus", "tota", "totum",
    "verus", "vera", "verum",
    "falsus", "falsa", "falsum",
    "clarus", "clara", "clarum",
    "pulcher", "pulchra", "pulchrum",
    "miser", "misera", "miserum",
    "liber", "libera", "liberum",
    "sacer", "sacra", "sacrum",
    "Romanus", "Romana", "Romanum",
    "Latinus", "Latina", "Latinum",
    "Graecus", "Graeca", "Graecum",
    "barbarus", "barbara", "barbarum",
    # Adjectives — 3rd declension
    "fortis", "forte", "fortes", "fortia",
    "gravis", "grave", "graves", "gravia",
    "levis", "leve",
    "brevis", "breve",
    "similis", "simile",
    "facilis", "facile",
    "difficilis", "difficile",
    "nobilis", "nobile",
    "humilis", "humile",
    "tristis", "triste",
    "dulcis", "dulce",
    "felix", "felicis", "felicem", "felices",
    "infelix", "infelicis",
    "acer", "acris", "acre",
    "celer", "celeris", "celere",
    # Adverbs
    "nunc", "tum", "tunc", "iam", "etiam", "autem",
    "ergo", "igitur", "enim", "nam", "ita", "sic",
    "ubi", "quo", "illic", "ibi", "inde", "hinc",
    "nusquam", "ubique", "usquam",
    "saepe", "numquam", "semper", "interim", "statim", "mox",
    "bene", "male", "valde", "maxime", "magis", "minus",
    "celeriter", "graviter", "fortiter", "libere", "facile",
    "subito", "repente", "tandem", "denique",
    "cur", "ideo", "propterea",
    "quomodo", "ut",
    "quam", "quantum", "tot", "quot",
    "nimis", "nimium", "parum", "satis",
    "fere", "quasi", "prope",
    "non", "haud", "ne", "neque", "nec",
    "et", "ac", "atque", "sed", "at", "vel", "aut",
    # Prepositions
    "in", "ad", "de", "ex", "ab", "per", "sub", "pro", "cum",
    "ante", "post", "inter", "super", "trans", "contra", "sine",
    "propter", "apud", "circa", "prae",
    # Numbers
    "unus", "una", "unum", "duo", "duae",
    "tres", "tria", "quattuor", "quinque", "sex",
    "septem", "octo", "novem", "decem",
    "viginti", "triginta", "centum", "mille",
    # Philosophical / rhetorical vocabulary
    "ratio", "rationis", "ratione",
    "sapientia", "sapientiae",
    "prudentia", "prudentiae",
    "iustitia", "iustitiae",
    "fortitudo", "fortitudinis",
    "temperantia", "temperantiae",
    "philosophia", "philosophiae",
    "rhetorica", "rhetoricae",
    "grammatica", "grammaticae",
    "historia", "historiae",
    "memoria", "memoriae",
    "sententia", "sententiae", "sententiam", "sententias",
    "epistula", "epistulae", "epistulam",
    "littera", "litterae", "litteram", "litteras",
    # De Bello Gallico key terms
    "legio", "legionis", "legionem", "legiones",
    "cohors", "cohortis", "cohortem", "cohortes",
    "acies", "aciei", "aciem",
    "victoria", "victoriae",
    "castra", "castrorum", "castris",
    "fossa", "fossae", "fossam",
    "vallum", "valli",
    "obsidio", "obsidionis",
    # Miscellaneous high-frequency
    "causa", "causae", "causam", "causis",
    "poena", "poenae", "poenam",
    "mora", "morae", "moram",
    "arma", "armorum", "armis",
    "telum", "teli", "tela",
    "scutum", "scuti", "scuta",
    "hasta", "hastae", "hastam", "hastas",
    "tabula", "tabulae", "tabulam",
    "pecunia", "pecuniae", "pecuniam",
    "copia", "copiae", "copiam", "copias",
    "inopia", "inopiae", "inopiam",
    "diligentia", "diligentiae",
    "industria", "industriae",
    "amicitia", "amicitiae", "amicitiam",
    "disciplina", "disciplinae",
]


def transcribe_word(transcriber, word: str) -> str | None:
    """Return IPA for a Latin word, or None if transcription fails."""
    try:
        result = transcriber.transcribe(word, macronise=False)
        if result and result.strip():
            return result.strip()
    except TypeError:
        # Some CLTK versions don't accept macronise keyword
        try:
            result = transcriber.transcribe(word)
            if result and result.strip():
                return result.strip()
        except Exception:
            pass
    except Exception:
        pass
    return None


def build_pls(words: list[str], output_path: str) -> None:
    try:
        from cltk.phonology.lat.transcription import Transcriber
        transcriber = Transcriber(dialect="Classical", reconstruction="Allen")
        use_cltk = True
    except ImportError:
        print(
            "Warning: cltk not installed — dictionary will contain only manually curated entries.\n"
            "Run: pip install cltk",
            file=sys.stderr,
        )
        use_cltk = False
        transcriber = None

    root = ET.Element("lexicon")
    root.set("version", "1.0")
    root.set("xmlns", "http://www.w3.org/2005/01/pronunciation-lexicon")
    root.set("alphabet", "ipa")
    root.set("xml:lang", "la")

    added = 0
    failed = 0
    already_added: set[str] = set()

    # Proper nouns first (manually curated, highest priority)
    for grapheme, phoneme in PROPER_NOUNS.items():
        lexeme = ET.SubElement(root, "lexeme")
        ET.SubElement(lexeme, "grapheme").text = grapheme
        ET.SubElement(lexeme, "phoneme").text = phoneme
        already_added.add(grapheme)
        added += 1

    # CLTK-transcribed words
    if use_cltk:
        for word in words:
            if word in already_added:
                continue
            phoneme = transcribe_word(transcriber, word)
            if phoneme:
                lexeme = ET.SubElement(root, "lexeme")
                ET.SubElement(lexeme, "grapheme").text = word
                ET.SubElement(lexeme, "phoneme").text = phoneme
                already_added.add(word)
                added += 1
            else:
                failed += 1

    # Pretty-print via minidom (works on all Python 3.x)
    raw = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(raw)
    pretty = dom.toprettyxml(indent="  ", encoding="UTF-8")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(pretty)

    print(f"Dictionary written to: {output_path}")
    print(f"  {added} entries added, {failed} words skipped (no CLTK transcription)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a PLS pronunciation dictionary for classical Latin"
    )
    parser.add_argument(
        "--output",
        default="data/latin_pronunciation.pls",
        help="Output PLS file path (default: data/latin_pronunciation.pls)",
    )
    parser.add_argument(
        "--word-list",
        help="Optional file with one Latin word per line to include alongside built-in vocabulary",
    )
    args = parser.parse_args()

    words = list(CORE_LATIN_WORDS)

    if args.word_list:
        with open(args.word_list) as f:
            extra = [line.strip() for line in f if line.strip() and line.strip().isalpha()]
        words.extend(extra)
        print(f"Word list: {len(CORE_LATIN_WORDS)} built-in + {len(extra)} from {args.word_list}")
    else:
        print(f"Using built-in vocabulary ({len(words)} word forms)")

    build_pls(words, args.output)


if __name__ == "__main__":
    main()
