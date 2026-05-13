"""
LinkedIn connections cleanup — interactive, manual-confirm per removal.

Flow:
  1. Opens a visible Chromium window.
  2. You log in (and complete 2FA) manually.
  3. Press ENTER in the terminal when you are on linkedin.com (logged in).
  4. Script navigates to /mynetwork/invite-connect/connections/ and scrolls.
  5. For each connection whose first name looks Turkish, it scrolls the card
     into view, draws a red outline, and asks y/n/q in the terminal.
       y = remove this connection
       n = skip
       q = quit
  6. Every action is logged to removed.log next to this script.

Notes:
  - LinkedIn DOM changes often. If selectors break, run with HEADFUL and
    inspect; selectors are isolated at the top of the file.
  - Random 2.0–4.5s waits between removals to reduce automation signal.
  - You can close the browser window at any time to abort.
"""

from __future__ import annotations

import asyncio
import random
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, ElementHandle

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "removed.log"

CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"

# --- Turkish-name heuristic ----------------------------------------------------
# First-name allow-list of distinctly Turkish names. Kept conservative on
# ambiguous cross-cultural names (e.g. "Ali", "Can", "Deniz" are included
# because in a Turkish-heavy LinkedIn network they are overwhelmingly Turkish,
# but you'll still confirm each one).
TURKISH_FIRST_NAMES = {
    # male
    "mehmet","ahmet","mustafa","ali","hüseyin","huseyin","hasan","ibrahim",
    "ismail","osman","yusuf","murat","emre","burak","can","cem","deniz",
    "eren","furkan","gökhan","gokhan","hakan","kaan","kerem","levent","mert",
    "onur","ozan","serkan","tolga","tuna","uğur","ugur","volkan","yağız",
    "yagiz","yiğit","yigit","zafer","özgür","ozgur","çağrı","cagri","şahin",
    "sahin","şükrü","sukru","ümit","umit","ilker","berk","alper","anıl",
    "anil","arda","aykut","barış","baris","batuhan","bilal","bora","buğra",
    "bugra","burhan","caner","cenk","doğan","dogan","ediz","efe","ekrem",
    "ender","ergin","ersin","ertuğrul","ertugrul","fatih","ferhat","halil",
    "hamza","kadir","kemal","koray","kürşat","kursat","mahmut","metin",
    "necati","nuri","okan","oktay","orhan","ömer","omer","rıza","riza",
    "sabri","sedat","selçuk","selcuk","selim","serdar","sinan","süleyman",
    "suleyman","taner","tarık","tarik","taylan","timur","tunç","tunc",
    "turgay","turgut","veli","yalçın","yalcin","yavuz","abdullah","doruk",
    "engin","gürkan","gurkan","haluk","harun","ilhan","kayhan","macit",
    "muhammet","muhammed","mücahit","nazım","nazim","okay","rahmi","rüstem",
    "rustem","samet","savaş","savas","şener","sener","tamer","ufuk",
    "yiğitcan","yigitcan","ataberk","aytaç","aytac","bayram","erkan","erdem",
    "cengiz","tayfun","sezer","kazım","kazim","çetin","cetin","erol","akın",
    "akin","erdal","halit","ramazan","yakup","mansur","nedim","recep",
    "şeref","seref","tezcan","tuğrul","tugrul","vedat","yaşar","yasar",
    "zekeriya","ufuk","alperen","atalay","alparslan","altan","arif","atilla",
    "ayhan","aziz","baki","bedirhan","behçet","behcet","bekir","berat",
    "berkay","beytullah","bilgehan","bilgin","birol","bülent","bulent",
    "cahit","celal","cevdet","davut","dursun","ebubekir","emir","emirhan",
    "emrah","enes","enis","eray","ercüment","ercument","erdoğan","erdogan",
    "ergun","ersel","ertan","faruk","fevzi","gencer","göktuğ","goktug",
    "görkem","gorkem","gültekin","gultekin","hamdi","hamit","haşim","hasim",
    "hayrettin","heysen","hikmet","hüsnü","husnu","ibrahim","ibo","idris",
    "ihsan","ilhami","irfan","ishak","kağan","kagan","kasım","kasim",
    "kayıhan","kayhan","keşan","mahir","mahmut","mehmed","melih","melik",
    "melikşah","meliksah","mesut","metehan","midyat","muhsin","mümin",
    "mumin","müslüm","muslum","naci","necip","necmettin","nevzat","niyazi",
    "nurettin","oğuz","oguz","oğuzhan","oguzhan","oktan","onat","özcan",
    "ozcan","özkan","ozkan","özhan","ozhan","raif","reşat","resat","resul",
    "rıdvan","ridvan","rüştü","rustu","saffet","sait","salih","sami",
    "sancak","sefa","sefer","selami","seyfi","seyfullah","sezai","şenol",
    "senol","sertaç","sertac","servet","sıtkı","sitki","soner","şeyhmus",
    "seyhmus","şinasi","sinasi","şükrü","sukru","talip","tansel","tarkan",
    "tayyip","tekin","temel","teoman","tuncay","ufukcan","umur","ünal",
    "unal","ünsal","unsal","ünver","unver","vahit","vural","yağız","yagiz",
    "yalın","yalin","yamen","yener","yetkin","yiğit","yigit","yusuf",
    "yüksel","yuksel","yunus","ziya","zülfikar","zulfikar",
    # female
    "ayşe","ayse","fatma","emine","hatice","zeynep","elif","sevgi","selin",
    "pınar","pinar","gül","gul","esra","merve","büşra","busra","tuğçe",
    "tugce","aslı","asli","sibel","özge","ozge","çiğdem","cigdem","şule",
    "sule","defne","ebru","ece","eda","aysu","ceyda","dilek","duygu","funda",
    "gamze","gizem","hande","irem","melis","nazlı","nazli","nesrin","nihal",
    "nilgün","nilgun","pelin","sema","şeyma","seyma","tuba","yasemin","ayla",
    "aylin","ayşegül","aysegul","begüm","begum","berna","beste","betül",
    "betul","burcu","buse","canan","cansu","ceren","demet","derya","didem",
    "dilara","dilay","dilruba","ela","emel","evrim","fadime","ferda","feride",
    "fulya","gönül","gonul","gülbahar","gülçin","gulcin","gülşah","gulsah",
    "günay","gunay","handan","hülya","hulya","hilal","ilknur","inci","ipek",
    "irmak","kübra","kubra","lale","leyla","meltem","meral","müge","muge",
    "nagehan","nehir","nesibe","neslihan","nuray","oya","öykü","oyku",
    "perihan","rabia","saliha","şebnem","sebnem","sedef","selma","semra",
    "senem","serap","sevda","sevil","sevim","şeyda","seyda","şirin","sirin",
    "songül","songul","şükran","sukran","tülay","tulay","ümran","umran",
    "yelda","yıldız","yildiz","zehra","zerrin","hira","banu","bahar","beril",
    "bilge","cemre","dicle","eylül","eylul","filiz","lara","mine","naz",
    "özlem","ozlem","reyhan","sare","selen","tülin","tulin","açelya","acelya",
    "ayça","ayca","aysun","azra","başak","basak","beyza","bircan","birsen",
    "buket","cemile","ceyhan","çağla","cagla","çisem","cisem","dilşad",
    "dilsad","dilara","dudu","duru","ece","ecem","ecrin","ediz","ela","elçin",
    "elcin","ellen","ercan","esin","esma","eylem","fadime","fethiye","feyza",
    "fidan","fikriye","gizem","gönül","gülay","gulay","gülnaz","gulnaz",
    "gülnur","gulnur","gülşen","gulsen","hacer","halime","hayriye","hediye",
    "hicran","hilal","hira","hümeyra","humeyra","huriye","ilkay","ilkim",
    "ilknur","inci","irem","irmak","iyem","jale","jülide","julide","kader",
    "kadriye","kamile","kerime","kezban","kıymet","kiymet","leyla","mahinur",
    "makbule","melda","melek","melis","melisa","melodi","menekşe","menekse",
    "meral","müjde","mujde","müjgan","mujgan","müşerref","muserref","müzeyyen",
    "muzeyyen","nagehan","nalan","narin","nazan","necibe","necla","neslişah",
    "neslisah","nevin","nigar","nilay","nuran","nükhet","nukhet","nurdan",
    "nurgül","nurgul","ömür","omur","öner","oner","özden","ozden","özlem",
    "ozlem","özgül","ozgul","pakize","pelin","peri","perihan","pervin",
    "piraye","rana","reyhan","rüveyda","ruveyda","saadet","sabriye","sadiye",
    "sandra","sare","saadet","sebahat","seçil","secil","sedef","selcen",
    "selin","selma","semih","sena","senem","sercem","sergül","sergul","sertap",
    "şefika","sefika","şehnaz","sehnaz","şenay","senay","sengül","sengul",
    "şenol","senol","serra","sevcan","sevda","sevde","sevdiye","sevgi",
    "sevgül","sevgul","sevil","sevim","seyhan","seyran","sibel","sıla","sila",
    "simay","simge","sinem","songül","songul","suzan","tansu","tijen","tomris",
    "tülay","tulay","tülin","tulin","türkan","turkan","ulviye","ünsal","unsal",
    "ümran","umran","ümmühan","ummuhan","vildan","yağmur","yagmur","yelda",
    "yıldız","yildiz","yonca","zehra","zeynep","zümrüt","zumrut","zühre","zuhre",
    # additions — names previously seen as missed or near-miss
    "hazal","yaren","sude","atakan","alican","alim","artuğ","artug","abdurrahman",
    "abdulkadir","ahsen","aysel","beyhan","beyzanur","candan","cüneyt","cuneyt",
    "dervis","derviş","edip","emam","enver","erhan","ersel","eyyup","gazi",
    "gökçe","gokce","güven","guven","hamit","heysen","kazim","kazım","kenan",
    "lav","melike","mucahit","mehmetali","mihriban","muharrem","nihat","nisa",
    "nur","nurhayat","nurcan","onurcan","safa","semih","seray","sıla","sila",
    "süleyman","suleyman","tufan","umut","yankı","yanki","yunus","yusuf",
    "zehra","ihsan","iclal","irmak","alperen","atakan","artuğ","baran","barkın",
    "barkin","barlas","baturay","behzat","besir","beşir","bilgehan","birkan",
    "bora","boran","candaş","candas","ceyhun","çetin","cetin","çınar","cinar",
    "dağhan","daghan","deniz","derin","doğa","doga","ekin","emir","emirhan",
    "enes","ercan","erdal","erdem","erdoğan","erdogan","erim","erkan","erkut",
    "ertan","ertem","ertuğrul","ertugrul","esat","fethi","fırat","firat",
    "fuat","gencer","göktuğ","goktug","gökay","gokay","hakkı","hakki","halid",
    "halit","hayri","hilmi","hüsamettin","husamettin","ihsan","ilkay","ilker",
    "irem","kağan","kagan","kayhan","kazım","kazim","koray","levent","mansur",
    "mehdi","melih","mertcan","metehan","murathan","nadir","necdet","necmettin",
    "nejat","numan","özgün","ozgun","özhan","ozhan","özkan","ozkan","övgün",
    "ovgun","poyraz","ramazan","reha","resul","rıdvan","ridvan","rıfat","rifat",
    "rıza","riza","sabri","saim","saner","savaş","savas","sefa","sefer","selami",
    "selçuk","selcuk","sertaç","sertac","sezgin","sıtkı","sitki","soner","suat",
    "şafak","safak","şahin","sahin","şemsettin","semsettin","şenol","senol",
    "tahsin","talha","talip","tamer","tansel","tarık","tarik","tayfun","tezcan",
    "tolga","tugay","tuğkan","tugkan","tuncay","ufkun","uğurcan","ugurcan",
    "ulaş","ulas","umut","ümit","umit","vedat","yağız","yagiz","yalın","yalin",
    "yaman","yamen","yaşar","yasar","yiğithan","yigithan","zekeriya","zeynel",
    # female extras
    "alev","alkım","alkim","arzu","ayben","ayça","ayca","aydan","aynur","azize",
    "bahar","banu","başak","basak","behiye","belgin","belkıs","belkis","belma",
    "benan","berfu","berivan","berna","berrak","berran","beşir","besir","beste",
    "betül","betul","beyhan","binnaz","birgül","birgul","birsen","cemile",
    "ceren","ceyhan","ceyhun","çağla","cagla","çiğdem","cigdem","çisem","cisem",
    "damla","derya","didem","dilan","dilara","duru","ebru","ece","ecem","ecrin",
    "elçin","elcin","elvan","emel","emine","emire","emrah","ercüment","ercument",
    "eslem","esma","eylem","eylül","eylul","fadime","fatma","fatoş","fatos",
    "feray","ferda","feride","feriha","feyza","fidan","fidanur","figen","fikriye",
    "filiz","fulya","funda","gamze","gizem","gönül","gonul","gözde","gozde",
    "gül","gul","gülay","gulay","gülçin","gulcin","gülden","gulden","güldeniz",
    "guldeniz","gülizar","gulizar","gülnaz","gulnaz","gülnur","gulnur","gülşah",
    "gulsah","gülşen","gulsen","günay","gunay","günel","gunel","hande","handan",
    "hatice","havva","hilal","hilmiye","hülya","hulya","ilkay","ilknur","inci",
    "ipek","irem","irmak","jale","kader","kadriye","kamile","kerime","kezban",
    "lale","leyla","mahinur","makbule","melahat","melek","meliha","melike","melis",
    "melisa","menekşe","menekse","meral","merve","mihriban","müge","muge","müjde",
    "mujde","müjgan","mujgan","müzeyyen","muzeyyen","nagehan","nalan","narin",
    "nazan","nazlı","nazli","necibe","necla","neslihan","nevin","nigar","nilay",
    "nilgün","nilgun","nuran","nurcan","nuriye","öykü","oyku","özden","ozden",
    "özge","ozge","özgül","ozgul","özlem","ozlem","perihan","pervin","pelin",
    "pınar","pinar","rabia","rana","reyhan","saadet","sabriye","sare","sebahat",
    "seçil","secil","seda","sedef","selen","selcen","selma","semra","sena",
    "senem","serap","sercem","sergül","sergul","sevda","sevde","sevgi","sevgül",
    "sevgul","sevil","sevim","seyhan","sibel","simge","sinem","songül","songul",
    "şükriye","sukriye","tansu","tomris","tülay","tulay","tülin","tulin","türkan",
    "turkan","ülkü","ulku","ümran","umran","ümmühan","ummuhan","vildan","yağmur",
    "yagmur","yelda","yıldız","yildiz","yonca","zehra","zerrin","zümrüt","zumrut",
    "zühre","zuhre",
}

TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜâîû")
TURKISH_SURNAME_SUFFIXES = ("oğlu", "oglu", "gil", "ler", "lar")

# Common Turkish surnames (ASCII-form so we catch romanized names too).
TURKISH_SURNAMES = {
    "yilmaz","yildiz","yildirim","ozturk","ozdemir","ozkan","ozer","ozcan",
    "celik","sahin","demir","kaya","aydin","arslan","aslan","dogan","kara",
    "koc","kurt","polat","sen","seker","sezen","sezgin","simsek","sungur",
    "tas","tasdemir","tekin","topal","topcu","tunc","turan","turker","ucar",
    "ulusoy","ulu","unal","uslu","yalcin","yavuz","yener","yesil","yildirim",
    "yuksel","akin","akkaya","aksoy","alkan","altun","altunkaya","arican",
    "ari","aritay","atik","ayan","ayaz","aydogan","ayhan","ayik","aykac",
    "bal","balci","balta","barut","bas","basar","basaran","battal","bayar",
    "baykal","bayraktar","bekir","bektas","berber","beser","beydir","bilgin",
    "birinci","bostan","bostanci","boyaci","bozkurt","budak","bulut","cakir",
    "cakmak","caliskan","celebi","cetin","cinar","cirak","corap","danisman",
    "delice","demirci","demirdogen","demirel","deniz","dere","dogru","dolek",
    "duman","durak","duru","duysak","ediz","ekici","ekin","ekmek","engin",
    "er","erdem","erdogan","eren","erkoca","ersoy","ertugrul","es","fidan",
    "gencer","goksu","gokman","gulec","guler","guller","gulseven","guman",
    "gunduz","gungor","gurkan","gurseven","gursoy","gursu","hayta","ilhan",
    "ilkdas","inal","inan","ince","incir","isik","ismail","kabakulak","kaçar",
    "kalkan","kaplan","kara","karaca","karaduman","karahan","karakaya",
    "karakoc","karakurt","karaoglu","karaoglu","karaduman","karatas","kart",
    "kasap","kaval","kavak","kayhan","kemal","kepenek","keskin","keskinkilic",
    "kilic","kilinc","kiyici","koc","kocaoglu","koksal","komurcu","koprulu",
    "kor","koroglu","koru","kose","kucuk","kulte","kurdoglu","kurtalan",
    "madak","mavi","metin","mete","mutlu","nazli","nurlu","odabas","oguz",
    "okumus","okur","oral","oran","ordu","oraz","oren","ortakaya","ozaydin",
    "ozdemir","ozdogan","ozhan","ozinan","ozkan","ozulu","peker","pinar",
    "polat","saglam","sakar","saracoglu","sarica","sarikaya","savran","savas",
    "sayin","secen","selik","sener","sener","sevinc","sezer","sezgin","sezici",
    "simsek","subasi","subaşı","sungur","sutcu","sutluoglu","tahtaci","takci",
    "taskin","taskan","tat","tahir","tatli","temizel","tetik","teymuroglu",
    "tigli","tirpan","tokat","tonus","topcu","torun","torunoglu","tunc",
    "tunca","turan","turhan","turker","turkyilmaz","turkmen","tutuncu","uctas",
    "ucar","ugur","ulusoy","unalan","unalir","uner","uslu","ustundag","uyar",
    "uygun","uzun","vural","yagiz","yaldirgan","yapan","yardim","yargic",
    "yavuz","yayla","yaylaoglu","yelkovan","yener","yerlikaya","yesil","yesim",
    "yesiltas","yigit","yigitcan","yilan","yildirim","yilmaz","yolal","yoruk",
    "yuksel","yurtdakal","zengin","zorlu","akcura","akcay","akgul","akguc",
    "akyol","arica","aksu","arica","asik","aydemir","aytac","ayyildiz",
    "balta","basaran","batuhan","baykal","bektas","benli","berber","bilgin",
    "bingul","bingoloğlu","birgili","boran","bostan","bostanci","budak",
    "buyuk","camci","canbul","ceylan","cetinkaya","cingoz","cinkilic","copur",
    "cubuk","dalkilic","dalakli","dayioglu","delibalta","delipalta","demirbas",
    "demirbilek","demirdogen","demiroz","dolek","duyar","ediz","ekmen",
    "emiroglu","ergun","erturk","ertul","eyigun","gokgul","gokman","gulec",
    "gulseven","gultek","gulten","gumus","guneri","gunes","gungor","hadi",
    "hazar","hobekkaya","incir","inceoz","kahveci","kara","karabay","karaca",
    "karacam","karahan","karaman","karaoglu","kasap","katkat","keklik",
    "kepenek","kesedar","kose","koroglu","kosar","kose","kucuk","kuru",
    "kurşun","kütle","kutle","lider","mardin","metin","ocak","ogretmen",
    "oz","ozaydin","ozeylem","ozinan","ozkan","ozulu","pakdemir","pala",
    "pamukcu","peker","sahin","saracoglu","sayan","seven","sezer","sezgin",
    "siler","sumer","sungur","tatari","taskan","tat","tayyar","tekin","temel",
    "teymuroglu","tigli","tokmak","topcu","topcuoglu","tunc","tuncel","turhan",
    "ucar","unal","unsal","unver","uras","urgan","ustündag","yagmur","yaldir",
    "yandi","yasin","yeniler","yerli","yetik","yiğit","yildiz","yilmaz",
    "yolal","yuksel","yuktas","yurtdakal","zengin","zorlu","akbaba","akbal",
    "alemdag","altinok","altun","altuntas","apaydin","arvas","aydin","azim",
    "balta","bay","bek","beker","bel","beyazit","beyaz","bingologlu","birkan",
    "bocek","caglar","cakirsoy","calik","capacioglu","cetinkaya","cetinkol",
    "cetiner","cetinkaya","cetinok","cetinkilic","cingoz","cinkilic","cizmeci",
    "copur","cubukcu","dagdelen","dalakli","dayioglu","demirhan","dere",
    "deveci","dogan","dolek","dumlu","duymaz","duysak","duyar","dumlu",
    "ediz","ekmek","eraslan","eraslan","erdogan","eren","erkaya","erkoca",
    "ertan","erturk","ertugrul","es","ferah","fidan","fidangul","gokce",
    "gokgul","gokmen","gucluyer","guler","guneri","gunes","gungor","gurkan",
    "gursoy","gursu","hayta","hobekkaya","ilkdas","incir","inceoz","incir",
    "kahveci","kabakulak","kakar","kale","kalin","karahan","karaca","karadag",
    "karakaya","karakoc","karakurt","karakus","karaman","karaoglu","karatas",
    "kasap","kasapoglu","katkat","kaval","kavak","kelmen","kepenek","kesedar",
    "keskin","keskinkilic","kilic","kilinc","kose","kucuk","kuru","kurt",
    "kutle","levent","liderakkoc","lokman","mengul","mert","metin","mete",
    "mutlu","nurlu","obu","odabas","oguz","okumus","okur","oral","oran",
    "ordu","oraz","ortagi","oren","ortakaya","ozay","ozalcin","ozaydin",
    "ozcan","ozdemir","ozer","ozkan","ozulu","pakdemir","pala","pamukcu",
    "peker","sagir","sahin","saracoglu","sarica","sarikaya","saral","savran",
    "sayan","saygi","seker","sen","sener","sengun","serhat","serim","seven",
    "sezer","sezgin","sezici","siler","sungur","sutcu","subasi","tahtaci",
    "takci","tat","tas","tasdemir","taskan","taskin","tasli","tat","tek",
    "tekin","tekkaya","teoman","temel","tetik","teymuroglu","tigli","tokat",
    "tokmak","tonus","topcu","torun","torunoglu","tunc","tunca","turan",
    "turhan","turker","tutuncu","ucar","ugur","ulu","ulus","ulutas","unal",
    "unalan","unalir","unsal","unver","uras","uygun","uzun","vural","yagiz",
    "yaldirgan","yandi","yapan","yardim","yargic","yasin","yavuz","yaylaoglu",
    "yelkovan","yener","yerli","yesil","yesim","yesiltas","yigit","yildiz",
    "yilmaz","yolal","yoruk","yuksel","yurtdakal","zengin","zorlu",
}

# Turkish words common in headlines/titles — strong signal person is Turkish.
# "ve"/"ile" intentionally OMITTED because they collide with Slavic languages
# (e.g. Slovak "ve" = "in"). Use longer, more distinctive words.
TURKISH_HEADLINE_WORDS = {
    "mühendis","muhendis","yazılım","yazilim","geliştirici","gelistirici",
    "uzman","uzmanı","uzmani","danışman","danisman","danışmanı","danismani",
    "müdür","mudur","müdürü","muduru","öğrenci","ogrenci","öğrencisi",
    "öğretmen","ogretmen","memur","çalışan","calisan","sorumlu","sorumlusu",
    "yönetici","yonetici","yöneticisi","yoneticisi","satış","satis",
    "satışı","satisi","pazarlama","kaynakları","kaynaklari",
    "muhasebe","muhasebeci","ticaret","destek","destekçi","destekci",
    "operasyon","tedarik","sevkiyat","analist","analisti","stajyer","staj",
    "araştırmacı","arastirmaci","bilişim","bilisim","bilgisayar","programcı",
    "programci","mühendisi","muhendisi","müşavir","musavir","müşavirliği",
    "musavirligi","üniversite","universite","üniversitesi","universitesi",
    "fakülte","fakulte","fakültesi","fakultesi","lisans","yüksek","yuksek",
    "yüksekokul","yuksekokul","okul","okulu","kurumunda","şirketinde",
    "sirketinde","türkiye","turkiye","istanbul","ankara","izmir","bursa",
    "kocaeli","kayseri","gaziantep","konya","adana","antalya","mersin",
    "samsun","trabzon","eskişehir","eskisehir","sivas","malatya","diyarbakır",
    "diyarbakir","manisa","balıkesir","balikesir","sanayi","tic","san","aş",
    "a.ş","ltd","şti","sti","sti̇","i̇nşaat","insaat","gıda","gida",
    "kimya","makine","elektrik","elektronik","gümrük","gumruk","ihracat",
    "ithalat","muhabir","mühasebe","yapım","yapim","mimar","mimarı","mimari",
    "doçent","docent","profesör","profesor","öğretim","ogretim","müdürlüğü",
    "mudurlugu","bakanlığı","bakanligi","koordinatör","koordinator",
    "koordinatörü","koordinatoru","stajyeri","yardımcı","yardimci",
    "yardımcısı","yardimcisi","kıdemli","kidemli","baş","bas","başkan",
    "baskan","başkanı","baskani","sanayi","sanayii","ticaret","i̇ş","is",
    "iş","işletme","isletme","işletmeciliği","isletmeciligi","muhabir",
    "tasarımcı","tasarimci","tasarım","tasarim","grafik","reklam","emlak",
    "sigorta","bankacılık","bankacilik","bankası","bankasi","kredi",
    "muhasebeci","mali","finans","finansman","bütçe","butce","hukuk",
    "avukat","avukatı","avukati","hâkim","hakim","savcı","savci","doktor",
    "hemşire","hemsire","eczacı","eczaci","ebe","veteriner","ziraat",
    "ziraat mühendisi","cağrı","cagri","cağrı merkezi","müdür yardımcısı",
    "uzman yardımcısı","emin","kaynak","insan kaynakları",
}

# Turkish company / institution name fragments often in headlines.
TURKISH_COMPANY_FRAGMENTS = {
    "akbank","garanti","yapı kredi","yapi kredi","ziraat","halkbank",
    "vakıfbank","vakifbank","türk telekom","turk telekom","türkcell","turkcell",
    "vodafone türkiye","arçelik","arcelik","beko","vestel","koç","kocsistem",
    "koç sistem","sabancı","sabanci","sabancıholding","eczacıbaşı","eczacibasi",
    "tüpraş","tupras","petkim","aselsan","tusaş","tusas","tav","mng","thy",
    "türk hava yolları","pegasus","onur air","anadolu","yapı endüstri",
    "yildiz holding","yıldız holding","ülker","ulker","torku","torku şeker",
    "ford otosan","tofaş","tofas","oyak","kale","akkök","akkok","akfen",
    "borusan","brisa","goodyear türkiye","trendyol","hepsiburada","getir",
    "yemeksepeti","n11","gittigidiyor","sahibinden","letgo","logo yazılım",
    "logo yazilim","netaş","netas","milsoft","havelsan","stm","roketsan",
    "bmc","fnss","otokar","temsa","mercedes türk","mercedes turk","mercedesturk",
    "anadolu sigorta","aksigorta","allianz türkiye","metropol","fibabanka",
    "denizbank","kuveyt türk","kuveyt turk","albaraka","türkiye finans",
    "ttnet","superonline","metaverse","koc holding","koç holding","aktif bank",
    "ing türkiye","ing turkiye","hsbc türkiye","odeabank","türk eximbank",
    "siemens türkiye","siemens turkiye","abb türkiye","schneider türkiye",
    "ericsson türkiye","huawei türkiye","ibm türkiye","ibm turkiye",
    "microsoft türkiye","microsoft turkiye","oracle türkiye","oracle turkiye",
    "sap türkiye","sap turkiye","accenture türkiye","accenture turkiye",
    "deloitte türkiye","pwc türkiye","ey türkiye","kpmg türkiye","ntt data",
    "trabzon","sivas","cumhuriyet üniversitesi","cumhuriyet universitesi",
    "i̇nönü","inonu","gazi üniversitesi","gazi universitesi","odtü","odtu",
    "boğaziçi","bogazici","itü","itu","istanbul teknik","yıldız teknik",
    "yildiz teknik","hacettepe","ankara üniversitesi","ankara universitesi",
    "ege üniversitesi","ege universitesi","dokuz eylül","dokuz eylul",
    "marmara üniversitesi","marmara universitesi","sakarya üniversitesi",
    "sakarya universitesi","yıldız","yildiz","türkiye sigorta",
    "türkiye finans","turkiye finans","koç sistem","koc sistem","türk hava",
    "turk hava","yapı kredi","yapi kredi","detaysoft","spro teknoloji",
    "metasis","aynet teknoloji","aselsan","türk akgıda","turk akgida",
}

# Companies/keywords the user wants always removed (case-insensitive).
TARGET_COMPANY_KEYWORDS = [
    r"\bsap\b",
    r"ebebek",
    r"e[\- ]?bebek",
    r"ak[\s\-]?gıda",   # akgıda, ak gıda, ak-gıda
    r"ak[\s\-]?gida",   # akgida, ak gida, ak-gida
    r"türk[\s\-]?akgıda",
    r"turk[\s\-]?akgida",
    r"lactalis",
]
TARGET_COMPANY_RE = re.compile("|".join(TARGET_COMPANY_KEYWORDS), re.IGNORECASE)


def looks_turkish_name(full_name: str) -> tuple[bool, str]:
    if not full_name:
        return False, ""
    name = full_name.strip()
    parts = re.split(r"\s+", name)
    first = parts[0].lower().strip(".,")
    if first in TURKISH_FIRST_NAMES:
        return True, f"first:{first}"
    if any(ch in TURKISH_CHARS for ch in name):
        return True, "tr-char"
    last = parts[-1].lower().strip(".,") if len(parts) > 1 else ""
    if last in TURKISH_SURNAMES:
        return True, f"surname:{last}"
    for suf in TURKISH_SURNAME_SUFFIXES:
        if last.endswith(suf) and len(last) > len(suf) + 1:
            return True, f"suffix:{suf}"
    # second name token also checked (some have middle names)
    for tok in parts[1:-1]:
        t = tok.lower().strip(".,")
        if t in TURKISH_FIRST_NAMES or t in TURKISH_SURNAMES:
            return True, f"mid:{t}"
    return False, ""


def looks_turkish_headline(headline: str) -> tuple[bool, str]:
    if not headline:
        return False, ""
    if any(ch in TURKISH_CHARS for ch in headline):
        return True, "headline-tr-char"
    low = headline.lower()
    for w in TURKISH_HEADLINE_WORDS:
        if len(w) < 4:
            continue  # skip very short words to avoid Slavic/EN collisions
        if re.search(rf"\b{re.escape(w)}\b", low):
            return True, f"headline-word:{w}"
    for frag in TURKISH_COMPANY_FRAGMENTS:
        if frag in low:
            return True, f"company:{frag}"
    return False, ""


def should_remove(name: str, headline: str) -> tuple[bool, str]:
    # 1) Company/SAP keyword in headline — highest priority
    m = TARGET_COMPANY_RE.search(headline or "")
    if m:
        return True, f"keyword:{m.group(0).lower()}"
    # 2) Turkish name
    is_tr, reason = looks_turkish_name(name)
    if is_tr:
        return True, reason
    # 3) Turkish-language headline
    is_th, reason = looks_turkish_headline(headline or "")
    if is_th:
        return True, reason
    return False, ""


# --- Logging ------------------------------------------------------------------

def log(line: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {line}"
    print(msg)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


# --- Async stdin prompt -------------------------------------------------------

async def ask(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(None, input, prompt)).strip().lower()


# --- LinkedIn interaction -----------------------------------------------------

# LinkedIn changes DOM frequently. We detect cards by walking up from each
# profile link (a[href*="/in/"]) inside main to the nearest row-like ancestor
# that ALSO contains a Message button — that's the connection card.
CARD_DISCOVERY_JS = r"""
() => {
  // Each connection row has a kebab button with aria-label
  // "More actions for <Full Name>". From that button we climb up to find
  // the row container (one that contains "Connected on" text) and extract
  // the headline (the line between name and "Connected on").
  const main = document.querySelector('main') || document.body;
  const buttons = Array.from(main.querySelectorAll('button[aria-label^="More actions for "]'));
  const cards = [];
  for (const b of buttons) {
    const label = b.getAttribute('aria-label') || '';
    const m = label.match(/^More actions for\s+(.+?)\s*$/i);
    if (!m) continue;
    const name = m[1].trim();
    if (!name) continue;

    // Climb up until we find an ancestor that includes "Connected on".
    let row = b.parentElement;
    for (let i = 0; i < 10 && row && row !== main; i++, row = row.parentElement) {
      const t = row.innerText || '';
      if (/connected on/i.test(t)) break;
    }
    let headline = '';
    if (row) {
      const lines = (row.innerText || '').split('\n').map(s => s.trim()).filter(Boolean);
      // headline = lines between the name line and the "Connected on" line
      let nameIdx = lines.findIndex(l => l === name);
      let connIdx = lines.findIndex(l => /^connected on/i.test(l));
      if (nameIdx >= 0 && connIdx > nameIdx) {
        headline = lines.slice(nameIdx + 1, connIdx).join(' | ');
      } else {
        // fallback: take lines that aren't name/connected/message
        headline = lines.filter(l => l !== name && !/^connected on/i.test(l) && !/^message$/i.test(l)).join(' | ');
      }
    }

    if (!b.dataset.cleanupId) {
      b.dataset.cleanupId = 'ck_' + Math.random().toString(36).slice(2, 10);
    }
    cards.push({ id: b.dataset.cleanupId, name: name, headline: headline });
  }
  return cards;
}
"""


async def highlight(card: ElementHandle, color: str = "red") -> None:
    try:
        await card.evaluate(
            "(el, c) => { el.style.outline = '3px solid ' + c; el.style.outlineOffset = '2px'; }",
            color,
        )
        await card.scroll_into_view_if_needed()
    except Exception:
        pass


async def unhighlight(card: ElementHandle) -> None:
    try:
        await card.evaluate("el => { el.style.outline = ''; el.style.outlineOffset = ''; }")
    except Exception:
        pass


async def click_remove(page: Page, kebab_el: ElementHandle, name: str) -> bool:
    """Click the kebab button, click Remove connection, confirm the modal."""
    try:
        await kebab_el.scroll_into_view_if_needed()
        await kebab_el.click()
        await page.wait_for_timeout(150)

        remove_item = page.locator(
            "div[role='menu'] >> text=/Remove connection/i, button:has-text('Remove connection'), [role='menuitem']:has-text('Remove connection')"
        ).first
        try:
            await remove_item.wait_for(state="visible", timeout=2000)
        except Exception:
            remove_item = page.locator("text=/Remove connection/i").first
            await remove_item.wait_for(state="visible", timeout=2000)
        await remove_item.click()
        await page.wait_for_timeout(250)

        # The confirmation modal's primary button ALSO reads "Remove connection"
        # (same text as the menu item) and the modal has no role=dialog. We
        # find the modal's Remove-connection button by looking for one that
        # has a sibling Cancel button.
        ok = await page.evaluate(r"""
        () => {
          const btns = Array.from(document.querySelectorAll('button'));
          // candidate: button whose text is "Remove connection" AND a Cancel
          // button exists in the same nearby container.
          const removeBtns = btns.filter(b => /^remove connection$/i.test((b.innerText||b.textContent||'').trim()));
          for (const rb of removeBtns) {
            // walk up a few levels looking for a Cancel sibling
            let p = rb.parentElement;
            for (let i = 0; i < 6 && p; i++, p = p.parentElement) {
              const cancel = Array.from(p.querySelectorAll('button')).find(b =>
                /^cancel$/i.test((b.innerText||b.textContent||'').trim())
              );
              if (cancel) {
                rb.click();
                return true;
              }
            }
          }
          return false;
        }
        """)
        if not ok:
            await page.keyboard.press("Escape")
            return False
        return True
    except Exception as e:
        log(f"  ! removal failed for {name}: {e}")
        try:
            await page.keyboard.press("Escape")
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def scroll_to_load_more(page: Page) -> bool:
    """Scroll to bottom; return True if new content appeared."""
    prev = await page.evaluate("document.body.scrollHeight")
    await page.mouse.wheel(0, 4000)
    await page.wait_for_timeout(1200)
    new = await page.evaluate("document.body.scrollHeight")
    return new > prev


# --- Main loop ----------------------------------------------------------------

async def run() -> None:
    log(f"=== session start, log file: {LOG_PATH} ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(viewport=None)
        page = await context.new_page()

        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        print("\n>>> LinkedIn login sayfası açıldı.")
        print(">>> Manuel login + 2FA tamamlayın, anasayfaya geldiğinizde terminale dönün.")
        await ask(">>> Login bitince ENTER'a basın... ")

        await page.goto(CONNECTIONS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        log("connections page loaded")

        seen_ids: set[str] = set()
        processed = 0
        removed = 0
        idle_scrolls = 0

        while True:
            cards = await page.evaluate(CARD_DISCOVERY_JS)
            if processed == 0 and not cards:
                diag = await page.evaluate(r"""
                () => {
                  const main = document.querySelector('main') || document.body;
                  const btns = main.querySelectorAll('button');
                  const links = main.querySelectorAll('a');
                  const msgs = Array.from(btns).filter(b => /message/i.test((b.innerText||b.textContent||'').trim()));
                  // detect shadow roots
                  let shadowCount = 0;
                  const walk = (n) => {
                    if (n.shadowRoot) shadowCount++;
                    for (const c of n.children || []) walk(c);
                  };
                  walk(main);
                  // collect first button labels
                  const sampleBtns = Array.from(btns).slice(0, 15).map(b => ({
                    text: (b.innerText||b.textContent||'').trim().slice(0,40),
                    aria: b.getAttribute('aria-label') || '',
                  }));
                  return {
                    buttonCount: btns.length,
                    linkCount: links.length,
                    msgButtonCount: msgs.length,
                    shadowCount,
                    sampleBtns,
                    bodyHTMLLen: document.body.innerHTML.length,
                  };
                }
                """)
                log(f"DIAG: {diag}")

            new_in_this_pass = 0
            for c in cards:
                cid = c["id"]
                name = c["name"]
                headline = c.get("headline", "")
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                new_in_this_pass += 1
                processed += 1

                remove, reason = should_remove(name, headline)
                if not remove:
                    continue

                kebab = await page.query_selector(f"button[data-cleanup-id='{cid}']")
                if not kebab:
                    log(f"  ! kebab vanished from DOM: {name}")
                    continue

                await highlight(kebab, "red")
                log(f"MATCH [{processed}]: {name} | {headline[:80]} | [{reason}]")
                ok = await click_remove(page, kebab, name)
                if ok:
                    removed += 1
                    log(f"REMOVED ({removed}): {name}")
                else:
                    log(f"FAILED: {name}")
                await page.wait_for_timeout(random.randint(600, 1200))

            if new_in_this_pass == 0:
                grew = await scroll_to_load_more(page)
                if not grew:
                    idle_scrolls += 1
                    if idle_scrolls >= 4:
                        log(f"no more connections to load. processed={processed} removed={removed}")
                        break
                else:
                    idle_scrolls = 0
            else:
                await scroll_to_load_more(page)
                idle_scrolls = 0

        print("\n>>> Bitti. Pencereyi kapatabilirsiniz.")
        await ask(">>> ENTER ile çık... ")
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
