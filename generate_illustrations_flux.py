"""
Flux Schnell 妖怪插画批量生成 - 含详细外貌提示词
每个妖怪都有基于西游记原文的白话文视觉描述
"""
import json, os, sys, time, argparse
import torch
from diffusers import FluxPipeline

MODEL_PATH = "/home/jckchen/FLUX.1-schnell"
OUTPUT_DIR = "illustrations"
TRIBULATIONS_FILE = "tribulations.json"
NUM_INFERENCE_STEPS = 4
GUIDANCE_SCALE = 0.0

# ============================================================
# 每个妖怪的详细视觉描述提示词
# 根据西游记原文描述，转化为白话文外貌特征
# ============================================================

DEMON_VISUALS = {
    # ── 人形妖怪 / 人 ──
    "刘洪": {
        "zh": "一名中年水贼，身材魁梧，满脸横肉，皮肤黝黑粗糙，络腮胡子，穿着粗布短褐衣衫，腰束麻绳，手持钢刀，面目凶恶狰狞，站在渡口船边。江边夜色背景。",
        "en": "a muscular middle-aged Chinese bandit with dark rough skin, thick beard, wearing coarse brown hemp clothes, holding a steel blade, fierce angry expression, standing by a river dock at night, Tang dynasty style"
    },
    "金池长老": {
        "zh": "一位老态龙钟的和尚，七十多岁，面如枯树皮，满脸皱纹，身穿金黄色锦斓袈裟，手持禅杖，头戴僧帽，贪婪的眼神，在观音禅院内。",
        "en": "an elderly Buddhist monk in his 70s, wrinkled face like old tree bark, wearing a golden kasaya robe, holding a monk staff, greedy sinister eyes, inside a temple hall"
    },
    "女儿国王": {
        "zh": "一位年轻貌美的女王，二十余岁，肌肤如雪，眉如远山，眼若秋水，头戴金凤冠，身穿大红锦袍，绣金凤图案，端坐龙椅之上，雍容华贵。",
        "en": "a beautiful young Chinese queen in her 20s, snow white skin, delicate eyebrows, wearing golden phoenix crown and red silk royal robe with gold embroidery, sitting on throne, elegant noble"
    },
    "寇洪": {
        "zh": "一位富态的老员外，身穿绸缎长袍，头戴员外帽，白须飘飘，慈眉善目，手持念珠。",
        "en": "a wealthy old Chinese merchant gentleman, wearing silk robes and a scholar hat, white beard, kind face, holding prayer beads"
    },
    "灭法国王": {
        "zh": "一位中年国王，身穿龙袍，头戴冕旒，面带怒气，坐在金銮殿龙椅上，手按宝剑。",
        "en": "a middle-aged Chinese king in dragon robe and imperial crown, angry expression, sitting on throne with hand on sword"
    },

    # ── 虎精 ──
    "寅将军(虎精)": {
        "zh": "一只直立行走的虎头妖怪，虎头人身，黄色虎皮上有黑色斑纹，血盆大口露出锋利獠牙，身穿破烂铠甲，手持长枪，背后是山洞。",
        "en": "a bipedal tiger demon with tiger head and muscular humanoid body, yellow fur with black stripes, sharp fangs protruding from mouth, wearing tattered armor, holding a long spear, standing before a cave"
    },

    # ── 熊精 ──
    "熊罴精": {
        "zh": "一只巨大的黑熊精，浑身黑色鬃毛，体型臃肿庞大，熊头人立，小眼睛闪着凶光，挥舞巨大的熊掌，指甲尖长如钩。",
        "en": "a massive black bear demon, huge bulky body covered in black fur, standing on hind legs, small fierce eyes, raising enormous clawed paws with hooked nails"
    },
    "特处士": {
        "zh": "一头野牛精，牛头人身，肌肉发达，两只弯曲的黑色牛角冲天，鼻孔喷着白气，皮肤灰黑粗糙，体型壮硕如小山。",
        "en": "a wild ox demon, muscular humanoid body with ox head, two curved black horns pointing upward, nostrils steaming, rough grey-black hide, massive bulky build"
    },
    "熊山君": {
        "zh": "一只棕熊精，棕色皮毛，体型硕大如小山，直立行走，熊头人脸混合，大嘴张开露出黄牙，爪子巨大。",
        "en": "a brown bear demon, massive body like a small mountain, standing upright, bear face with human features, gaping mouth showing yellow teeth, enormous claws"
    },

    # ── 龙 ──
    "西海龙王三太子(玉龙)": {
        "zh": "一条白色的玉龙，全身鳞片晶莹如玉，龙角珊瑚状，龙须飘动，身体修长优雅，盘旋在空中云雾之间，最终化为一匹白马。",
        "en": "a white jade dragon with translucent pearl-like scales, coral-shaped horns, flowing whiskers, long elegant serpentine body, coiled in clouds and mist, transforming into a white horse"
    },
    "鼍龙(泾河龙王之子)": {
        "zh": "一条黑色的鳄龙，类似巨大鳄鱼但更长，浑身黑色鳞甲坚硬如铁，长嘴布满利齿，四爪锋利，潜伏在黑水河中。",
        "en": "a black crocodile-dragon, like a giant armored crocodile with iron-hard black scales, long snout full of sharp teeth, sharp claws, lurking in dark river water"
    },

    # ── 猪八戒 ──
    "猪刚鬣(猪八戒)": {
        "zh": "一个猪头人身的妖怪，肥头大耳，长嘴獠牙，皮肤粗糙黝黑，大腹便便，身穿黑色直裰，手持九齿钉钯，鬃毛竖立如钢针。",
        "en": "a pig-headed humanoid demon, fat head with big floppy ears, long snout with tusks, rough dark skin, enormous pot belly, wearing black robes, holding a nine-tooth iron rake, bristly mane standing up like steel needles"
    },

    # ── 沙僧 ──
    "沙悟净(沙僧)": {
        "zh": "一个红发蓝脸的凶恶妖怪，一头蓬松的红发如火，靛蓝色面皮，脖子上挂着九个骷髅头串成的项链，手持降妖宝杖，身披破旧僧袍，赤脚站立。",
        "en": "a fierce demon with wild flaming red hair and indigo blue face, wearing a necklace of nine human skulls, holding a demon-subduing staff, tattered monk robe, barefoot, muscular build"
    },

    # ── 黑熊精 ──
    "黑熊精(黑风大王)": {
        "zh": "一只黑色狗熊精，浑身漆黑如墨的鬃毛，体型壮硕如铁塔，直立行走，头戴乌金盔，身穿黑铁甲，手持黑缨枪，站在黑风山洞口。",
        "en": "a black bear demon, pitch-black bristly fur, massive iron-tower-like build, standing upright, wearing dark iron helmet and black iron armor, holding a black-tasseled spear, before a dark cave entrance"
    },

    # ── 黄风怪 ──
    "黄风怪": {
        "zh": "一只黄毛貂鼠精，通体金黄色皮毛，身形灵敏小巧，尖嘴长须，眼睛贼亮，口吐黄色三昧神风旋涡，风力摧枯拉朽飞沙走石。",
        "en": "a golden-furred weasel demon, sleek golden yellow fur, small agile body, pointy snout with long whiskers, crafty bright eyes, spewing a yellow divine wind vortex that uproots trees and flings boulders"
    },

    # ── 白骨精 ──
    "白骨夫人(白骨精)": {
        "zh": "一具森森白骨化作的美貌女子，身穿白色衣裙，面容姣好但面色惨白如死人，周身阴气缭绕，指尖长出锋利骨刺，背后隐约可见骷髅虚影。",
        "en": "a skeletal demon appearing as a beautiful woman, wearing white dress, beautiful face but deathly pale complexion, surrounded by ghostly energy, sharp bone claws extending from fingertips, faint skulls visible behind her"
    },

    # ── 黄袍怪 ──
    "黄袍怪(奎木狼)": {
        "zh": "一个身穿黄色锦袍的高大妖怪，狼头人身，青面獠牙，狼眼闪着绿光，披着绣金纹的杏黄色长袍，手持追魂取命刀。",
        "en": "a tall wolf-headed demon wearing a splendid yellow brocade robe with gold embroidery, blue-green wolf face with fangs, glowing green eyes, holding a soul-chasing curved blade"
    },

    # ── 金角银角 ──
    "金角大王": {
        "zh": "一个头长金色独角的妖怪，童子模样但面目狰狞，金色独角从额头正中长出，身穿金红道袍，手托紫金红葫芦，腰间挂着幌金绳。",
        "en": "a demon boy with a single golden horn growing from forehead center, child-like but fierce face, wearing golden-red Daoist robe, holding a purple-gold-red gourd in hand, golden rope at waist"
    },
    "银角大王": {
        "zh": "一个头长银色独角的妖怪，与金角大王相似但银角银发，童子模样，身穿银白道袍，手托羊脂玉净瓶，阴沉冷峻。",
        "en": "a demon boy with a single silver horn, silver hair, child-like appearance, wearing silver-white Daoist robe, holding a white jade vase, cold sinister expression"
    },

    # ── 青毛狮子(乌鸡国) ──
    "青毛狮子(狮猁王)": {
        "zh": "一头青色毛发的巨大狮精，狮子头人立，鬃毛青绿蓬松如火焰，身穿国王龙袍冒充君主，体型庞大威猛，怒目圆睁。",
        "en": "a massive green-maned lion demon, lion head with fluffy green mane like flames, standing upright, wearing a king's dragon robe as disguise, huge imposing build, furious bulging eyes"
    },

    # ── 红孩儿 ──
    "红孩儿(圣婴大王)": {
        "zh": "一个七岁童子模样的妖怪，面如傅粉唇若涂朱，身穿红肚兜，赤脚，手持丈八火尖枪，口吐三昧真火，周身火焰环绕，站在火云洞口。",
        "en": "a demon child appearing as a 7-year-old boy, powdered white face with vermillion lips, wearing only a red belly-band, barefoot, holding a long fire-tipped spear, breathing out samadhi true fire, surrounded by flames"
    },

    # ── 虎力鹿力羊力 ──
    "虎力大仙": {
        "zh": "一头老虎精化作的道士，身穿黄色道袍，虎须微微露出，身形高大威猛，手执拂尘，道貌岸然但虎目有凶光。",
        "en": "a tiger demon disguised as a Daoist priest, wearing yellow Daoist robe, tiger whiskers slightly visible, tall powerful build, holding a horsetail whisk, dignified but with fierce tiger eyes"
    },
    "鹿力大仙": {
        "zh": "一头白鹿精化作的道士，身穿白色道袍，头戴道冠，身形清瘦，面容清秀但有狡黠之相，手持拂尘。",
        "en": "a white deer demon disguised as a Daoist priest, wearing white Daoist robe and priest hat, slender lean build, delicate face with cunning expression, holding a horsetail whisk"
    },
    "羊力大仙": {
        "zh": "一头羚羊精化作的道士，身穿灰色道袍，长须长眉，头上隐约可见弯曲羊角，身材瘦高，眼神阴冷。",
        "en": "an antelope demon disguised as a Daoist priest, wearing grey Daoist robe, long beard and eyebrows, curved horns barely visible on head, tall thin build, cold eyes"
    },

    # ── 灵感大王 ──
    "灵感大王(金鱼精)": {
        "zh": "一条巨大的金红色鲤鱼精，全身鳞片金光闪闪，鱼头人身，嘴边长须，身穿金甲，手持铜锤，蹲在通天河冰面上。",
        "en": "a giant gold-red koi fish demon, glistening golden scales all over, fish head with whiskers on humanoid body, wearing golden armor, holding a bronze hammer, crouching on frozen river surface"
    },

    # ── 青牛精 ──
    "青牛精(独角兕大王)": {
        "zh": "一头巨大的青牛精，皮肤青灰色，头生一只独角，牛头人身，肌肉虬结，鼻穿金环，手持一根金光闪闪的金刚琢，站在金兜洞口。",
        "en": "a massive green-grey bull demon, greenish-grey hide, single horn on forehead, muscular humanoid body with bull head, golden nose ring, holding a glowing diamond bracelet weapon, standing before a cave"
    },

    # ── 如意真仙 ──
    "如意真仙": {
        "zh": "一个道士模样的妖怪，白面长须，身穿青色道袍，头戴道冠，手持拂尘，坐在落胎泉边的石头上，神情傲慢。",
        "en": "a demon disguised as a Daoist immortal, pale face with long beard, wearing cyan Daoist robe and priest hat, holding a whisk, sitting by a mystical spring, arrogant expression"
    },

    # ── 蝎子精 ──
    "蝎子精": {
        "zh": "一个美貌女妖，身穿紫色纱裙，面容妖艳，但身后露出巨大的蝎子尾钩，尾尖闪着毒光，十指尖利如蝎钳，盘坐在琵琶洞口。",
        "en": "a beautiful seductive female demon in purple gauze dress, enchanting face, but with a giant scorpion tail hook behind her glowing with venom, fingers like pincers, sitting at cave entrance"
    },

    # ── 六耳猕猴 ──
    "六耳猕猴(假悟空)": {
        "zh": "一只与孙悟空一模一样的猴妖，雷公嘴，孤拐面，火眼金睛，头戴金箍，身穿虎皮裙，手持如意金箍棒，但长着六只耳朵，眼神更加狡诈。",
        "en": "a monkey demon identical to Sun Wukong, thunder-god beak mouth, gaunt monkey face, fiery golden eyes, golden headband, tiger-skin kilt, holding a magical iron staff, but with six ears, more cunning eyes"
    },

    # ── 铁扇公主/牛魔王 ──
    "铁扇公主(罗刹女)": {
        "zh": "一个中年美妇，身穿翠绿纱裙，头戴银簪，手持一柄巨大的芭蕉扇，面容端庄但带怒气，站在芭蕉洞口。",
        "en": "a beautiful middle-aged woman in emerald green silk dress, silver hairpins, holding an enormous palm-leaf fan, dignified but angry face, standing before a cave entrance"
    },
    "牛魔王": {
        "zh": "一头巨大的白色牛精，浑身白毛，头长一对巨大的弯曲牛角，牛头人身，身形巨大如山，身穿金甲红袍，手持混铁棍，威猛无比。",
        "en": "a colossal white bull demon, white fur all over, massive curved bull horns, mountain-sized muscular humanoid body with bull head, wearing golden armor and red cape, holding a giant iron club, overwhelmingly powerful"
    },

    # ── 九头虫 ──
    "九头虫": {
        "zh": "一个长着九个头的巨大鸟形妖怪，每个头都是狰狞的鸟头，羽毛暗绿，九个长颈从身体伸出，翅膀巨大可以遮天，站在碧波潭边。",
        "en": "a giant bird-like demon with nine heads, each a ferocious bird head on a long neck, dark green feathers, nine necks sprouting from one body, enormous wings that blot out the sky, standing by a lake"
    },
    "万圣龙王": {
        "zh": "一条老龙，鳞片灰绿色，龙角苍老多节，龙须白而长，身穿龙袍，坐在碧波潭龙宫中。",
        "en": "an old dragon with grey-green scales, gnarled ancient horns, long white whiskers, wearing dragon robes, sitting in an underwater palace"
    },

    # ── 树精/杏仙 ──
    "荆棘岭十八公(树精)": {
        "zh": "一个老翁模样的树精，枯瘦如松，皮肤如老树皮般粗糙满是裂纹，身穿褐色粗袍，须发皆白如树根，手拄木杖，站在荆棘丛中。",
        "en": "an old tree spirit appearing as a thin elderly man, skin like rough cracked tree bark, wearing coarse brown robes, white hair and beard like roots, holding a wooden staff, standing among thorny bushes"
    },
    "杏仙": {
        "zh": "一个美貌的杏花仙子，身穿粉色纱裙，头戴杏花冠，面色粉嫩如杏花，身姿婀娜，身边飘落粉色花瓣。",
        "en": "a beautiful apricot blossom fairy in pink gauze dress, wearing a crown of apricot flowers, cheeks pink as blossoms, graceful elegant posture, pink petals falling around her"
    },

    # ── 黄眉大王 ──
    "黄眉大王": {
        "zh": "一个假扮如来佛的妖怪，坐在莲台上冒充佛祖，金色袈裟，螺髻发型，但眉毛是黄色的，面容虽然庄严但眼神狡诈，手持人种袋。",
        "en": "a demon pretending to be Buddha, sitting on lotus throne in golden kasaya, spiral hair bun, but with distinct yellow eyebrows, face appears dignified but eyes are cunning, holding a magical cloth bag"
    },

    # ── 大蟒精 ──
    "大蟒精": {
        "zh": "一条巨大的蟒蛇成精，蛇身粗如水缸，浑身漆黑鳞片闪着暗光，蛇头巨大如斗，红信吞吐，盘踞在七绝山稀柿衕中，躯体绵延数十丈。",
        "en": "a giant python demon, body thick as a water vat, pitch-black scales with dark gleam, head huge as a basket, red forked tongue flicking, coiled in a putrid mountain pass, body stretching for hundreds of feet"
    },

    # ── 赛太岁 ──
    "赛太岁(金毛犼)": {
        "zh": "一只金毛犼，外形似狮子但全身金色鬃毛，体型巨大如象，头生独角，相貌威猛如麒麟与狮子的混合体，脖子上挂着紫金铃，站在麒麟山獬豸洞口。",
        "en": "a golden-haired hou, lion-like beast with golden mane covering entire body, massive as an elephant, single horn on head, like a mix of qilin and lion, wearing a purple-gold bell necklace, standing at cave entrance"
    },

    # ── 蜘蛛精 ──
    "七个蜘蛛精": {
        "zh": "七个美貌女妖，各穿赤橙黄绿青蓝紫七色纱裙，容貌娇媚，每人都能从肚脐眼吐出白色蛛丝，坐在盘丝洞中织网。",
        "en": "seven beautiful spider demonesses, each wearing a different color silk dress of the rainbow, seductive appearances, each able to spray white spider silk from their navels, sitting in a cave weaving webs"
    },

    # ── 百眼魔君 ──
    "百眼魔君(多目怪)": {
        "zh": "一个道士模样的蜈蚣精，身穿金色道袍，头戴道冠，看似仙风道骨，但两胁之下有上千只眼睛，张开道袍时千目齐放金光毒雾。",
        "en": "a centipede demon disguised as a Daoist priest, wearing golden Daoist robe and hat, appears immortal-like, but has a thousand eyes under his ribs, when opening his robe all eyes emit blinding golden toxic light"
    },

    # ── 狮驼岭三妖 ──
    "青狮精": {
        "zh": "一头巨大的青毛狮子精，青色鬃毛蓬松如云，狮子头人立，獠牙如剑，身穿金甲，体型如山，站在狮驼洞口，口中可吞十万天兵。",
        "en": "a colossal blue-green lion demon, fluffy cyan mane like clouds, lion head with sword-like fangs, wearing golden armor, mountain-sized, standing at cave entrance, mouth capable of swallowing armies"
    },
    "白象精": {
        "zh": "一头巨大的白象精，通体白皮，象头人身，长鼻如巨蟒可卷人，獠牙雪白如弯刀，体型如山岳，身穿银甲，站在狮驼洞口。",
        "en": "a colossal white elephant demon, pure white hide, elephant head with trunk like a giant python, white tusks like curved swords, mountain-sized, wearing silver armor, at cave entrance"
    },
    "大鹏金翅雕": {
        "zh": "一只巨大的金翅大鹏鸟，双翅展开如垂天之云，金色羽毛闪闪发光，鹰头利爪，双眼如闪电，站立时翅膀可遮日月，最凶恶的妖怪。",
        "en": "a giant golden-winged roc bird, wings spanning like clouds covering the sky, gleaming golden feathers, eagle head with deadly talons, eyes like lightning, wings blot out the sun when spread, the most fearsome demon"
    },

    # ── 白鹿精/狐狸精 ──
    "白鹿精(国丈)": {
        "zh": "一只白鹿精化作的老人，白发白须，身穿白色道袍，看似仙风道骨的老神仙，实际是妖怪国丈，手持龙头拐杖，身形清瘦。",
        "en": "a white deer demon disguised as an elderly man, white hair and beard, wearing white Daoist robes, appears like an immortal sage but is actually a demon, holding a dragon-head cane, thin build"
    },
    "白面狐狸精": {
        "zh": "一只白狐精化作的美艳女子，面如银盘，狐媚眼，身穿白色裘皮，身后隐隐露出蓬松狐尾，妖艳异常。",
        "en": "a white fox demon disguised as a stunning beauty, silver-white face, seductive fox eyes, wearing white fur coat, fluffy fox tail faintly visible behind, extremely alluring"
    },

    # ── 老鼠精 ──
    "金鼻白毛老鼠精(地涌夫人)": {
        "zh": "一只白毛老鼠精化作的美女，面容俏丽，皮肤雪白，身穿白色纱裙，但鼻子是金色的，小巧尖鼻闪着金光，身后隐约有鼠尾，住在无底洞中。",
        "en": "a white-furred mouse demoness appearing as a beauty, pretty face, snow-white skin, wearing white gauze dress, but with a distinctive golden nose tip gleaming, mouse tail faintly visible, dwelling in a bottomless cave"
    },

    # ── 豹子精 ──
    "豹子精(南山大王)": {
        "zh": "一只花豹精，豹头人身，黄色皮毛上布满黑色金钱斑纹，身形矫健灵活，穿皮甲，手持钢叉，站在隐雾山折岳连环洞口。",
        "en": "a leopard demon, leopard head with yellow fur covered in black rosette spots, agile muscular humanoid body, wearing leather armor, holding a steel trident, at cave entrance in misty mountains"
    },

    # ── 黄狮精 ──
    "黄狮精": {
        "zh": "一头黄色狮子精，通体黄毛，鬃毛金黄蓬松，狮子头人身，体格壮硕，身穿黄袍，偷偷盗走金箍棒九齿钯和降妖杖，在竹节山洞中。",
        "en": "a yellow lion demon, golden-yellow fur all over, fluffy golden mane, lion head on muscular humanoid body, wearing yellow robes, sneaking away with stolen magical weapons, inside a cave"
    },

    # ── 九灵元圣 ──
    "九灵元圣(九头狮)": {
        "zh": "一只巨大的九头狮子，体型庞大如山，九个狮子头从身体伸出，每个头都有蓬松鬃毛，主头最大最威猛，一声吼可开九幽之门，最强大的妖怪之一。",
        "en": "a colossal nine-headed lion, mountain-sized body, nine lion heads each with fluffy mane sprouting from body, central head the largest and most fierce, one roar can open gates to the underworld, one of the most powerful demons"
    },

    # ── 犀牛精 ──
    "辟寒大王": {
        "zh": "一头巨大的犀牛精，皮肤灰黑如铁，头生一只巨大独角，体型壮硕如小山，身穿金甲，站在玄英洞中，呼吸间寒气逼人。",
        "en": "a giant rhinoceros demon, iron-grey hide, single enormous horn on nose, massive build like a small mountain, wearing golden armor, standing in a cave, breathing out freezing cold air"
    },
    "辟暑大王": {
        "zh": "一头红色犀牛精，皮肤赤红如铜，独角弯曲向后，体型与辟寒大王相似，周身散发灼热之气。",
        "en": "a red rhinoceros demon, copper-red hide, curved backward-pointing horn, similar massive build, radiating intense heat"
    },
    "辟尘大王": {
        "zh": "一头黄色犀牛精，皮肤土黄，独角短粗，体型壮硕，周身尘土飞扬，站在玄英洞前。",
        "en": "a yellow rhinoceros demon, earth-yellow hide, short thick horn, massive build, surrounded by swirling dust clouds, at cave entrance"
    },

    # ── 玉兔精 ──
    "玉兔精": {
        "zh": "一只月宫玉兔化作的美丽公主，身穿白色绣花宫装，头戴珍珠冠，面容如月般皎洁，身姿婀娜，手持绣球，站在彩楼之上。",
        "en": "a moon rabbit demoness disguised as a beautiful princess, wearing white embroidered palace dress and pearl crown, face bright as the moon, graceful figure, holding a silk ball, standing on a decorated tower"
    },

    # ── 蜘蛛精(单只) ──
    "蜘蛛精": {
        "zh": "一只盘丝洞的蜘蛛精，人形美女但下半身连着巨大蜘蛛腹，八条蛛腿从背后伸出，身穿彩衣，口吐白丝。",
        "en": "a spider demoness, beautiful woman upper body but connected to giant spider abdomen below, eight spider legs extending from back, wearing colorful clothes, spewing white silk from mouth"
    },

    # ── 四圣化身 ──
    "黎山老母、观音、普贤、文殊(化身)": {
        "zh": "四位菩萨化身为母女四人：一位白发老母和三位年轻貌美的女儿，各穿素雅衣裙，坐在庄园厅堂之中，面带慈悲之色，试探取经人的禅心。",
        "en": "four bodhisattvas disguised as a family: an elderly white-haired mother and three beautiful young daughters, each in simple elegant dress, sitting in a manor hall, compassionate faces, testing pilgrims' resolve"
    },

    # ── 镇元大仙 ──
    "镇元大仙(非妖怪)": {
        "zh": "一位道家神仙，头戴紫金冠，身穿八卦仙衣，手持拂尘，三缕长须飘胸，仙风道骨，身后是人参果树，树上挂着婴儿状的人参果。",
        "en": "a Daoist immortal, wearing purple-gold crown and eight-trigram immortal robe, holding a whisk, three long beard strands, sage-like appearance, behind him a ginseng fruit tree with baby-shaped fruits hanging"
    },

    # ── 白鼋 ──
    "白鼋(非妖怪)": {
        "zh": "一只巨大的白色老鼋，类似巨龟，白色龟壳有磨盘大，龟头从壳中伸出，龟眼充满期待地望着唐僧，浮在通天河水面。",
        "en": "a giant white softshell turtle, enormous white shell big as a millstone, head extended from shell, hopeful expectant eyes looking upward, floating on a wide river surface"
    },

    # ── 未分类 ──
    "灵感大王": {
        "zh": "一条巨大的金红色鲤鱼精，全身鳞片金光闪闪，鱼头人身，嘴边长须，身穿金甲，手持铜锤，蹲在通天河冰面上。",
        "en": "a giant gold-red koi fish demon, glistening golden scales, fish head on humanoid body, whiskers, wearing golden armor, holding bronze hammer, crouching on frozen river"
    },
}

# 默认视觉描述模板
DEFAULT_VISUAL = {
    "zh": "一个中国古代神话妖怪，中国传统工笔画风格，全身像，白底，细节丰富。",
    "en": "a Chinese mythological demon, full body portrait, traditional Chinese gongbi painting style, white background, highly detailed"
}


def load_pipeline():
    print("正在加载 Flux Schnell 模型...")
    pipe = FluxPipeline.from_pretrained(
        MODEL_PATH, torch_dtype=torch.bfloat16, local_files_only=True)
    print("  启用 sequential CPU offload...")
    pipe.enable_sequential_cpu_offload(gpu_id=0)
    print("  ✓ 模型就绪")
    return pipe


def build_prompt(demon_name, description):
    """构建详细视觉提示词"""
    visual = DEMON_VISUALS.get(demon_name, DEFAULT_VISUAL)

    # T5 长文本 — 中文详细外貌 + 风格
    prompt_t5 = (
        f"{visual['zh']}"
        f"这幅画采用中国传统工笔重彩画风格，线条精细流畅，色彩古朴典雅，"
        f"白色绢本底色，画面突出妖怪主体，唐代壁画韵味，"
        f"高清精细，如同博物馆级中国古典绘画。"
    )

    # CLIP 短文本 — 英文视觉关键词
    prompt_clip = (
        f"{visual['en']}, "
        f"traditional Chinese gongbi painting, Tang dynasty mural art, "
        f"ink brush lines, parchment background, masterpiece, highly detailed"
    )

    return prompt_t5, prompt_clip


def generate_image(pipe, demon_name, description, output_path, width=768, height=768):
    safe_name = demon_name.replace("/", "-").replace("、", "-")
    output_file = os.path.join(output_path, f"{safe_name}.png")

    if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
        print(f"  ✓ {demon_name} 已有，跳过")
        return True

    prompt_t5, prompt_clip = build_prompt(demon_name, description)
    seed = hash(demon_name) % (2**31)

    try:
        print(f"  生成中... ({width}x{height})")
        generator = torch.Generator(device="cpu").manual_seed(seed)

        image = pipe(
            prompt=prompt_t5, prompt_2=prompt_clip,
            width=width, height=height,
            num_inference_steps=NUM_INFERENCE_STEPS,
            guidance_scale=GUIDANCE_SCALE,
            generator=generator,
            max_sequence_length=256,
        ).images[0]

        image.save(output_file)
        print(f"  ✓ {demon_name} ({os.path.getsize(output_file)//1024}KB)")
        return True

    except torch.cuda.OutOfMemoryError:
        print(f"  ! OOM, 降级512x512...")
        try:
            image = pipe(
                prompt=prompt_t5, prompt_2=prompt_clip,
                width=512, height=512,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                generator=generator,
                max_sequence_length=128,
            ).images[0]
            image.save(output_file)
            print(f"  ✓ {demon_name} (降级)")
            return True
        except Exception as e:
            print(f"  ✗ 降级后仍失败: {e}")
            return False
    except Exception as e:
        print(f"  ✗ {demon_name}: {e}")
        return False


def get_unique_demons(tribulations):
    seen = set()
    demons = []
    for t in tribulations:
        for d in t['demons']:
            if d['name'] in {"无", "待考证"}:
                continue
            if d['name'] not in seen:
                seen.add(d['name'])
                demons.append(d)
    return demons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--name', type=str)
    parser.add_argument('--width', type=int, default=512)
    parser.add_argument('--height', type=int, default=512)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int, default=0)
    parser.add_argument('--force', action='store_true', help='强制重新生成已有插图')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(TRIBULATIONS_FILE, 'r', encoding='utf-8') as f:
        tribulations = json.load(f)

    demons = get_unique_demons(tribulations)

    if args.demo:
        demons = demons[:3]
    elif args.name:
        demons = [d for d in demons if args.name in d['name']]
        if not demons:
            all_d = get_unique_demons(tribulations)
            print(f"未找到 '{args.name}'，可用: {[d['name'] for d in all_d]}")
            sys.exit(1)
    elif args.count > 0:
        demons = demons[args.start:args.start + args.count]

    print(f"🎨 Flux Schnell 妖怪插画 ({len(demons)}个)")
    print(f"   尺寸: {args.width}x{args.height} | 步数: {NUM_INFERENCE_STEPS}")
    print()

    if args.force:
        for d in demons:
            safe = d['name'].replace("/", "-").replace("、", "-")
            path = os.path.join(OUTPUT_DIR, f"{safe}.png")
            if os.path.exists(path):
                os.remove(path)
        print("  已清除旧图，全部重新生成")

    pipe = load_pipeline()

    success = 0
    t0 = time.time()
    for i, demon in enumerate(demons):
        print(f"[{i+1}/{len(demons)}] {demon['name']}")
        t1 = time.time()
        if generate_image(pipe, demon['name'], demon['description'], OUTPUT_DIR, args.width, args.height):
            success += 1
            print(f"     耗时: {time.time()-t1:.0f}s")

    total = time.time() - t0
    print(f"\n{'='*50}")
    print(f"完成: {success}/{len(demons)} | 总耗时: {total/60:.0f}分钟")
    print(f"目录: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
