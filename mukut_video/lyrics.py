"""Allocate lyric lines to bars (approximate: proportional to text length within each vocal span)."""
import json
B = json.load(open("beats.json"))["bars"]; END = 248.4
def bar_t(x):  # fractional bar index -> seconds (linear between detected bars)
    i = int(x); i = max(0, min(i, len(B) - 1)); a = B[i]; b = B[i + 1] if i + 1 < len(B) else END
    return a + (b - a) * (x - i)
E = None
sections = [
 # (start_bar, end_bar, [(bn, en)])  bn-only English lines use en=None
 (0.4, 7.6, [("এই শহরে অনেকেই রাজা সাজে… কিন্তু সিংহাসন আর রাজত্ব— এক জিনিস নয়।", "In this city many play the king… but a throne and a kingdom are not the same."),
             ("আমি পরিচয় দিতে আসিনি, আমি উপস্থিতি জানান দিতে এসেছি।", "I didn't come to introduce myself. I came to announce my presence."),
             ("No crown needed… I was born with the code.", None)]),
 (8.0, 18.0, [("কালো গাড়ি, কালো রাত, চোখে রাজকীয় ঘুম,", "Black car, black night, royal sleep in my eyes,"),
              ("হাজার মুখের ভিড়ে আমি একাই নিজের ধুন।", "In a crowd of a thousand faces, I'm alone with my own tune."),
              ("কথা দিয়ে নয়, কাজ দিয়ে পরিচয়,", "Identity by deeds, not words,"),
              ("আমার নীরবতারও আলাদা একটা সময়।", "Even my silence has its own time."),
              ("যারা পাশে ছিল, সময় তাদের চিনিয়ে দিল,", "Time showed me who stood beside me,"),
              ("মুখোশের আড়ালে কে, আয়না বুঝিয়ে দিল।", "The mirror revealed who hid behind masks."),
              ("আমি কারও ছায়া নই, কারও অনুকরণ না,", "I'm nobody's shadow, nobody's imitation,"),
              ("নিজের পথের বাদশাহ, কারও অধীন না।", "King of my own path, under no one."),
              ("পকেটে স্বপ্ন, বুকে ক্ষত, চোখে ভবিষ্যৎ,", "Dreams in my pocket, scars in my chest, the future in my eyes,"),
              ("হারতে হারতে শিখেছি জেতার আসল অর্থ।", "Losing again and again, I learned what winning really means."),
              ("আমার গল্পে নেই কোনো সস্তা অভিনয়,", "No cheap acting in my story,"),
              ("আমি ঝড়ের সন্তান, নত হওয়া আমার নয়।", "I'm a child of the storm; bowing is not mine.")]),
 (18.4, 24.8, [("যত রাত গভীর হয়, তত চোখে আগুন জ্বলে।", "The deeper the night, the more fire in my eyes."),
               ("যত মানুষ দূরে যায়, তত নিজের কাছে ফিরি।", "The further people drift, the closer I return to myself."),
               ("আমি থামিনি, আমি হারিনি, শুধু নিজেকে বদলেছি…", "I haven't stopped, I haven't lost, I only changed myself…"),
               ("The king never falls, He learns how to rise.", None)]),
 (25.0, 34.8, [("আমি বাদশাহ, মুকুট আমার আত্মসম্মান,", "I'm the king, my crown is my self-respect,"),
               ("আমার নীরবতায় লেখা হাজার অভিমান।", "A thousand hurts written in my silence."),
               ("আমি কারও কাছে মাথা নত করি না,", "I bow to no one,"),
               ("নিজের বিবেক ছাড়া কারও ভয় করি না।", "I fear no one but my own conscience."),
               ("এই রাজত্ব রক্তে নয়, বিশ্বাসে গড়া,", "This kingdom isn't built on blood, but on belief,"),
               ("ঝড়ের বুকেও আমার পতাকা ওড়া।", "My flag flies even in the storm's heart."),
               ("Remember the name, remember the code, I walk alone, but I own my road!", None)]),
 (35.2, 50.8, [("বন্ধুত্বের নামে কত হিসাব দেখেছি,", "So many calculations I saw in the name of friendship,"),
               ("হাসিমুখের পেছনে কত ছুরি দেখেছি।", "So many knives behind smiling faces."),
               ("যে হাত ধরেছিল, সে হাত ছেড়ে গেল,", "The hand that held me let go,"),
               ("অন্ধকারে দাঁড়িয়ে সময় চিনিয়ে দিল।", "Standing in the dark, time taught me."),
               ("আমি প্রতিশোধের আগুনে জীবন পোড়াই না,", "I don't burn my life in the fire of revenge,"),
               ("ছোট মানুষের জন্য নিজের মান হারাই না।", "I don't lose my dignity over small people."),
               ("যে সম্মান দিতে জানে, সে সম্মান পায়,", "Who knows how to give respect, gets respect,"),
               ("যে বিশ্বাস ভাঙে, সে ইতিহাসে হারায়।", "Who breaks trust is lost in history."),
               ("No fake love, no fake friends, My loyalty has no loose ends.", None),
               ("আমি দাম দিয়ে মানুষ কিনতে আসিনি,", "I didn't come to buy people with a price,"),
               ("নিজের মূল্য কখনো বিক্রি করিনি।", "I never sold my own worth.")]),
 (51.3, 57.7, [("একটা সময় আমিও স্বপ্ন দেখতাম, কেউ একজন থাকবে, যে বুঝবে আমায়।", "Once I too dreamed someone would be there who understood me."),
               ("আজও সেই স্বপ্ন বুকের ভেতর থাকে, শুধু কাউকে আর বলি না…", "That dream still lives in my chest; I just don't tell anyone anymore…"),
               ("কারণ রাজা হলেও, রাতের শেষে মানুষ একাই থাকে।", "Because even a king, at the end of the night, is alone.")]),
 (59.0, 60.9, [("But pain made me powerful. Silence made me dangerous. And time made me royal.", None)]),
 (62.0, 75.0, [("আমি বাদশাহ, মুকুট আমার আত্মসম্মান,", "I'm the king, my crown is my self-respect,"),
               ("আমার নীরবতায় লেখা হাজার অভিমান।", "A thousand hurts written in my silence."),
               ("আমি কারও কাছে মাথা নত করি না,", "I bow to no one,"),
               ("নিজের বিবেক ছাড়া কারও ভয় করি না।", "I fear no one but my own conscience."),
               ("এই রাজত্ব রক্তে নয়, বিশ্বাসে গড়া,", "This kingdom isn't built on blood, but on belief,"),
               ("ঝড়ের বুকেও আমার পতাকা ওড়া।", "My flag flies even in the storm's heart."),
               ("Remember the name, remember the code, I walk alone, but I own my road!", None)]),
 (79.3, 81.2, [("আমার গল্প শেষ হয়নি… এটা তো কেবল শুরু।", "My story isn't over… this is only the beginning.")]),
 (81.4, 83.9, [("A king doesn't chase the throne. The throne remembers the king.", None)]),
]
caps = []
for a, b, lines in sections:
    t0, t1 = bar_t(a), bar_t(b); w = [len(l[0]) + (len(l[1]) * 0.6 if l[1] else 0) for l in lines]; tot = sum(w); t = t0
    for (bn, en), wi in zip(lines, w):
        d = (t1 - t0) * wi / tot
        caps.append({"t0": round(t + 0.05, 2), "t1": round(t + d - 0.08, 2), "bn": bn, "en": en}); t += d
json.dump(caps, open("captions.json", "w"), ensure_ascii=False, indent=1)
print(len(caps), "captions; first", caps[0]["t0"], "last", caps[-1]["t1"])
