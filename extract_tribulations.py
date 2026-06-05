"""
从西游记.txt 提取八十一难结构化数据
"""
import json
import re

def extract_tribulation_names(filepath):
    """从第6543行提取80难名称"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 第6543行（1-indexed）包含了80难的完整列表
    line = lines[6542]  # 0-indexed

    # 找到 "蒙差揭谛皈依旨谨记唐僧难数清：" 之后的内容
    start_marker = "谨记唐僧难数清："
    end_marker = "圣僧历难簿分明"

    start_idx = line.find(start_marker)
    end_idx = line.find(end_marker)

    if start_idx == -1:
        raise ValueError(f"未找到起始标记: {start_marker}")

    passage = line[start_idx + len(start_marker):end_idx]

    # 构建1-80的难序号列表
    # 1-10: 第X难 (第一难, 第二难, ..., 第十难)
    # 11-80: X难 (十一难, 十二难, ..., 八十难)
    cn_unit = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

    number_markers = []
    for i in range(1, 81):
        if i <= 10:
            marker = f'第{cn_unit[i]}难'
        elif i == 80:
            marker = '八十难'
        else:
            tens = i // 10   # 1, 2, ..., 7
            ones = i % 10
            tens_cn = '' if tens == 1 else cn_unit[tens]  # 十X not 一十X
            ones_cn = cn_unit[ones]
            marker = f'{tens_cn}十{ones_cn}难'
        number_markers.append(marker)

    # 用这些标记分割passage
    tribulations = []
    remaining = passage

    for idx, marker in enumerate(number_markers):
        pos = remaining.find(marker)
        if pos == -1:
            print(f"  警告: 未找到 '{marker}' (第{idx+1}难)")
            continue

        name = remaining[:pos]
        remaining = remaining[pos + len(marker):]

        tribulations.append({
            'index': idx + 1,
            'name': name.strip(),
            'marker': marker
        })

    if not tribulations:
        raise ValueError("未能解析八十一难列表")

    print(f"从原文解析出 {len(tribulations)} 难")
    return tribulations


def build_tribulations_dataset(names):
    """
    根据八十一难名称，补充妖怪、地点、事件等信息。
    基于西游记经典知识构建数据集。
    """
    # 对每一难的知识库 - 基于西游记原著
    knowledge = {
        "金蝉遭贬": {"demons": [{"name": "无", "description": "金蝉子因不听说法，轻慢大教，被贬真灵转生东土"}], "dangerLevel": 1, "events": ["金蝉子被贬下凡"], "location": "西天灵山", "chapterRef": "第12回"},
        "出胎几杀": {"demons": [{"name": "刘洪", "description": "水贼，打死陈光蕊，霸占殷温娇"}], "dangerLevel": 2, "events": ["唐僧出生", "殷温娇将婴儿放入木盆漂江"], "location": "洪江渡口", "chapterRef": "第9回"},
        "满月抛江": {"demons": [{"name": "刘洪", "description": "同上"}], "dangerLevel": 2, "events": ["殷温娇被迫将满月的唐僧放入江中"], "location": "江州", "chapterRef": "第9回"},
        "寻亲报冤": {"demons": [{"name": "刘洪", "description": "水贼"}], "dangerLevel": 2, "events": ["玄奘长大寻母", "报父仇", "刘洪被斩"], "location": "江州", "chapterRef": "第9回"},
        "出城逢虎": {"demons": [{"name": "寅将军(虎精)", "description": "双叉岭上的虎精，唐僧出长安后遇到的第一个妖怪"}], "dangerLevel": 2, "events": ["唐僧出长安城", "在双叉岭遇虎精"], "location": "双叉岭", "chapterRef": "第13回"},
        "落坑折从": {"demons": [{"name": "熊罴精", "description": "双叉岭上的熊精"}, {"name": "野牛精", "description": "双叉岭上的野牛精"}], "dangerLevel": 2, "events": ["唐僧落入坑中", "随从被妖怪吃掉"], "location": "双叉岭", "chapterRef": "第13回"},
        "双叉岭上": {"demons": [{"name": "寅将军", "description": "虎精"}, {"name": "特处士", "description": "野牛精"}, {"name": "熊山君", "description": "熊精"}], "dangerLevel": 3, "events": ["三妖同食唐僧随从", "太白金星解救唐僧"], "location": "双叉岭", "chapterRef": "第13回"},
        "两界山头": {"demons": [{"name": "无", "description": "孙悟空被压五行山下五百年"}], "dangerLevel": 1, "events": ["唐僧揭去压帖", "收孙悟空为大徒弟"], "location": "两界山(五行山)", "chapterRef": "第14回"},
        "陡涧换马": {"demons": [{"name": "西海龙王三太子(玉龙)", "description": "西海龙王之子，因纵火烧了殿上明珠被贬，在蛇盘山鹰愁涧等待取经人"}], "dangerLevel": 2, "events": ["白龙吃掉唐僧白马", "观音菩萨点化白龙为马"], "location": "蛇盘山鹰愁涧", "chapterRef": "第15回"},
        "夜被火烧": {"demons": [{"name": "金池长老", "description": "观音禅院的老院主，贪心唐僧袈裟"}, {"name": "黑风山黑熊精", "description": "黑风山的黑熊精，偷走锦斓袈裟"}], "dangerLevel": 3, "events": ["金池长老纵火烧禅院", "袈裟被黑熊精盗走"], "location": "观音禅院", "chapterRef": "第16回"},
        "失却袈裟": {"demons": [{"name": "黑熊精(黑风大王)", "description": "黑风山上修行的黑熊精，善使黑缨枪，与金池长老交友"}], "dangerLevel": 3, "events": ["黑熊精盗走锦斓袈裟", "孙悟空寻回袈裟", "观音收黑熊精为守山大神"], "location": "黑风山黑风洞", "chapterRef": "第17回"},
        "收降八戒": {"demons": [{"name": "猪刚鬣(猪八戒)", "description": "原为天蓬元帅，因调戏嫦娥被贬下凡，错投猪胎，在高老庄作怪"}], "dangerLevel": 2, "events": ["高老庄收猪八戒", "猪八戒拜师唐僧"], "location": "高老庄", "chapterRef": "第18-19回"},
        "黄风怪阻": {"demons": [{"name": "黄风怪", "description": "黄风岭黄风洞中的妖怪，原是灵山脚下的黄毛貂鼠，偷吃琉璃盏内的清油成精，善使三昧神风"}], "dangerLevel": 3, "events": ["黄风怪掳走唐僧", "灵吉菩萨用飞龙杖降妖"], "location": "黄风岭黄风洞", "chapterRef": "第20-21回"},
        "请求灵吉": {"demons": [{"name": "黄风怪", "description": "同上，三昧神风无人能挡"}], "dangerLevel": 3, "events": ["孙悟空求助灵吉菩萨", "灵吉菩萨用定风丹和飞龙杖降妖"], "location": "小须弥山", "chapterRef": "第21回"},
        "流沙难渡": {"demons": [{"name": "沙悟净(沙僧)", "description": "原为卷帘大将，因打碎琉璃盏被贬流沙河，每七日受飞剑穿胸之苦"}], "dangerLevel": 2, "events": ["流沙河收沙僧为徒", "沙僧拜师唐僧"], "location": "流沙河", "chapterRef": "第22回"},
        "收得沙僧": {"demons": [{"name": "沙悟净", "description": "同上"}], "dangerLevel": 1, "events": ["木叉行者劝降沙僧", "唐僧收沙僧为三徒弟"], "location": "流沙河", "chapterRef": "第22回"},
        "四圣显化": {"demons": [{"name": "黎山老母、观音、普贤、文殊(化身)", "description": "四圣化为母女四人，以招赘试探取经人禅心"}], "dangerLevel": 1, "events": ["四圣试禅心", "八戒出丑被绑在树上"], "location": "西牛贺洲某庄院", "chapterRef": "第23回"},
        "五庄观中": {"demons": [{"name": "镇元大仙(非妖怪)", "description": "地仙之祖，五庄观观主，有人参果树"}], "dangerLevel": 3, "events": ["偷吃人参果", "推倒人参果树", "与镇元大仙斗法"], "location": "万寿山五庄观", "chapterRef": "第24回"},
        "难活人参": {"demons": [{"name": "镇元大仙", "description": "同上"}], "dangerLevel": 3, "events": ["孙悟空求观音医活人参果树", "镇元大仙与孙悟空结为兄弟"], "location": "五庄观", "chapterRef": "第26回"},
        "贬退心猿": {"demons": [{"name": "白骨夫人(白骨精)", "description": "白虎岭上的尸魔，善变化，先后化为少女、老妪、老翁来欺骗唐僧"}], "dangerLevel": 3, "events": ["三打白骨精", "唐僧误会悟空滥杀", "悟空被赶回花果山"], "location": "白虎岭", "chapterRef": "第27回"},
        "黑松林失散": {"demons": [{"name": "黄袍怪(奎木狼)", "description": "二十八宿之奎木狼星下凡，在碗子山波月洞为妖，掳走宝象国公主百花羞"}], "dangerLevel": 4, "events": ["唐僧在黑松林迷路自投波月洞", "唐僧被黄袍怪抓住"], "location": "黑松林碗子山波月洞", "chapterRef": "第28回"},
        "宝象国捎书": {"demons": [{"name": "黄袍怪", "description": "同上"}], "dangerLevel": 4, "events": ["公主托唐僧送信给宝象国王", "黄袍怪到宝象国将唐僧变成老虎"], "location": "宝象国", "chapterRef": "第29回"},
        "金銮殿变虎": {"demons": [{"name": "黄袍怪(奎木狼)", "description": "在宝象国金銮殿施法将唐僧变成老虎"}], "dangerLevel": 4, "events": ["唐僧在金銮殿被变成老虎", "白龙马化为人形刺杀黄袍怪", "八戒去花果山请回悟空"], "location": "宝象国", "chapterRef": "第30回"},
        "平顶山逢魔": {"demons": [{"name": "金角大王", "description": "太上老君的看金炉童子"}, {"name": "银角大王", "description": "太上老君的看银炉童子，偷了老君五件宝物下凡"}], "dangerLevel": 4, "events": ["银角大王移山压住悟空", "妖怪掳走唐僧、八戒、沙僧"], "location": "平顶山莲花洞", "chapterRef": "第32-33回"},
        "莲花洞高悬": {"demons": [{"name": "金角大王、银角大王", "description": "同上，有五件宝物：紫金红葫芦、羊脂玉净瓶、七星剑、芭蕉扇、幌金绳"}], "dangerLevel": 4, "events": ["悟空被收入葫芦", "悟空用计反收二妖", "太上老君收回二童子"], "location": "平顶山莲花洞", "chapterRef": "第34-35回"},
        "乌鸡国救主": {"demons": [{"name": "青毛狮子(狮猁王)", "description": "文殊菩萨的坐骑，将乌鸡国国王推入井中，自己做了三年假国王"}], "dangerLevel": 3, "events": ["孙悟空揭穿假国王", "从井中捞出真国王", "文殊菩萨收回坐骑"], "location": "乌鸡国", "chapterRef": "第37-39回"},
        "被魔化身": {"demons": [{"name": "青毛狮子", "description": "同上，曾变化成唐僧模样"}], "dangerLevel": 3, "events": ["假唐僧被揭穿"], "location": "乌鸡国", "chapterRef": "第39回"},
        "号山逢怪": {"demons": [{"name": "红孩儿(圣婴大王)", "description": "牛魔王和罗刹女之子，在火焰山修行三百年炼成三昧真火"}], "dangerLevel": 4, "events": ["红孩儿掳走唐僧", "三昧真火烧退悟空"], "location": "号山枯松涧火云洞", "chapterRef": "第40-41回"},
        "风摄圣僧": {"demons": [{"name": "红孩儿", "description": "同上，用狂风掳走唐僧"}], "dangerLevel": 4, "events": ["红孩儿化风掠走唐僧"], "location": "号山", "chapterRef": "第40回"},
        "心猿遭害": {"demons": [{"name": "红孩儿", "description": "三昧真火使悟空险些丧命"}], "dangerLevel": 5, "events": ["悟空被三昧真火烧成重伤", "八戒请观音反被红孩儿冒充观音捉住"], "location": "号山", "chapterRef": "第41回"},
        "请圣降妖": {"demons": [{"name": "红孩儿", "description": "最终被观音菩萨收服"}], "dangerLevel": 4, "events": ["孙悟空请观音菩萨降伏红孩儿", "观音用玉净瓶甘露灭火", "红孩儿被收为善财童子"], "location": "号山", "chapterRef": "第42回"},
        "黑河沉没": {"demons": [{"name": "鼍龙(泾河龙王之子)", "description": "泾河龙王的第九子，在衡阳峪黑水河为妖"}], "dangerLevel": 3, "events": ["唐僧被拖入黑水河", "孙悟空请西海龙王太子摩昂降妖"], "location": "衡阳峪黑水河", "chapterRef": "第43回"},
        "搬运车迟": {"demons": [{"name": "虎力大仙", "description": "黄毛虎精，在车迟国冒充道士"}, {"name": "鹿力大仙", "description": "白毛鹿精"}, {"name": "羊力大仙", "description": "羚羊精"}], "dangerLevel": 3, "events": ["三妖在车迟国迫害和尚", "孙悟空大闹三清观"], "location": "车迟国", "chapterRef": "第44回"},
        "大赌输赢": {"demons": [{"name": "虎力大仙、鹿力大仙、羊力大仙", "description": "同上，与悟空师徒斗法"}], "dangerLevel": 3, "events": ["祈雨", "云梯显圣", "隔板猜枚", "砍头剖腹下油锅", "三妖身死"], "location": "车迟国", "chapterRef": "第45-46回"},
        "祛道兴僧": {"demons": [{"name": "虎力、鹿力、羊力大仙", "description": "三妖死后，车迟国恢复佛教"}], "dangerLevel": 2, "events": ["车迟国国王重新尊佛", "释放所有和尚"], "location": "车迟国", "chapterRef": "第47回"},
        "路逢大水": {"demons": [{"name": "灵感大王(金鱼精)", "description": "观音菩萨莲花池里养大的金鱼，每日浮头听经修成手段，在通天河为妖"}], "dangerLevel": 3, "events": ["通天河阻路", "灵感大王每年要村民献祭童男童女"], "location": "通天河", "chapterRef": "第47回"},
        "身落天河": {"demons": [{"name": "灵感大王", "description": "施法冻住通天河，趁唐僧过河时破冰捉人"}], "dangerLevel": 4, "events": ["通天河结冰", "唐僧徒步过河", "冰破人落水被擒"], "location": "通天河", "chapterRef": "第48回"},
        "鱼篮现身": {"demons": [{"name": "灵感大王(金鱼精)", "description": "被观音用鱼篮收回"}], "dangerLevel": 3, "events": ["观音菩萨编鱼篮来收妖", "金鱼精被收回南海"], "location": "通天河", "chapterRef": "第49回"},
        "金山遇怪": {"demons": [{"name": "青牛精(独角兕大王)", "description": "太上老君的坐骑青牛偷了金刚琢下凡，在金兜山金兜洞为妖"}], "dangerLevel": 4, "events": ["唐僧被青牛精所擒", "金刚琢收走悟空金箍棒和各路神兵"], "location": "金兜山金兜洞", "chapterRef": "第50回"},
        "普天神难伏": {"demons": [{"name": "青牛精(独角兕大王)", "description": "金刚琢可套走一切兵器法宝"}], "dangerLevel": 5, "events": ["悟空请来天兵天将均被套走兵器", "十八罗汉的砂丹也被收走", "如来暗示青牛来历"], "location": "金兜山", "chapterRef": "第51回"},
        "问佛根源": {"demons": [{"name": "青牛精", "description": "太上老君说：若无芭蕉扇，我也不能奈他何"}], "dangerLevel": 4, "events": ["如来暗示后悟空找太上老君", "太上老君用芭蕉扇收服青牛"], "location": "金兜山", "chapterRef": "第52回"},
        "吃水遭毒": {"demons": [{"name": "如意真仙", "description": "牛魔王的兄弟，霸占解阳山破儿洞的落胎泉"}], "dangerLevel": 2, "events": ["唐僧、八戒误饮子母河水怀孕", "悟空与如意真仙争夺落胎泉水"], "location": "西梁女国解阳山", "chapterRef": "第53回"},
        "西梁国留婚": {"demons": [{"name": "女儿国王(非妖怪)", "description": "西梁女国国王，貌美多情，欲招唐僧为夫"}], "dangerLevel": 1, "events": ["女王欲招唐僧为夫", "唐僧假意应允后离开"], "location": "西梁女国", "chapterRef": "第54回"},
        "琵琶洞受苦": {"demons": [{"name": "蝎子精", "description": "曾在灵山听如来佛讲经，如来推了她一把，她用尾针刺伤如来，逃到琵琶洞。善使倒马毒桩"}], "dangerLevel": 4, "events": ["蝎子精掳走唐僧欲成亲", "悟空八戒被倒马毒刺伤", "昴日星官降服蝎子精"], "location": "毒敌山琵琶洞", "chapterRef": "第55回"},
        "再贬心猿": {"demons": [{"name": "六耳猕猴(假悟空)", "description": "混世四猴之一，善聆音能察理，知前后万物皆明。化作悟空模样打伤唐僧"}], "dangerLevel": 5, "events": ["假悟空打伤唐僧抢走行李", "二悟空大战难以分辨", "打到地府找谛听辨真伪", "如来佛认出六耳猕猴"], "location": "西行路上", "chapterRef": "第56-57回"},
        "难辨猕猴": {"demons": [{"name": "六耳猕猴", "description": "与真悟空一模一样，观音、玉帝、地府都不能分辨"}], "dangerLevel": 5, "events": ["二猴打到观音面前", "打到天庭照妖镜", "打到地府", "如来佛分辨后六耳猕猴被悟空打死"], "location": "西天灵山", "chapterRef": "第58回"},
        "路阻火焰山": {"demons": [{"name": "铁扇公主(罗刹女)", "description": "牛魔王之妻，红孩儿之母，掌有芭蕉扇"}, {"name": "牛魔王", "description": "七大圣之首，力量与悟空相当"}], "dangerLevel": 4, "events": ["火焰山阻路无法通过", "悟空借芭蕉扇被铁扇公主拒绝"], "location": "火焰山", "chapterRef": "第59回"},
        "求取芭蕉扇": {"demons": [{"name": "铁扇公主、牛魔王", "description": "牛魔王变成猪八戒骗回芭蕉扇"}], "dangerLevel": 4, "events": ["悟空变成小虫进入铁扇公主腹中", "骗到假扇子越扇火越大", "变成牛魔王骗到真扇"], "location": "火焰山芭蕉洞", "chapterRef": "第60回"},
        "收缚魔王": {"demons": [{"name": "牛魔王", "description": "被四大金刚、天兵天将、孙悟空等围剿"}], "dangerLevel": 5, "events": ["悟空大战牛魔王", "天兵天将四大金刚围剿", "牛魔王被哪吒降伏", "用芭蕉扇扇灭火焰山"], "location": "火焰山", "chapterRef": "第61回"},
        "赛城扫塔": {"demons": [{"name": "九头驸马(九头虫)", "description": "乱石山碧波潭万圣龙王的女婿，九头虫，偷了祭赛国金光寺的佛宝舍利子"}], "dangerLevel": 3, "events": ["悟空八戒扫金光寺塔", "发现妖怪盗宝秘密"], "location": "祭赛国金光寺", "chapterRef": "第62回"},
        "取宝救僧": {"demons": [{"name": "九头虫", "description": "被二郎神和悟空联手击败"}, {"name": "万圣龙王", "description": "碧波潭龙王"}], "dangerLevel": 3, "events": ["悟空八戒大战九头虫", "二郎神相助打伤九头虫", "夺回佛宝舍利子"], "location": "乱石山碧波潭", "chapterRef": "第63回"},
        "棘林吟咏": {"demons": [{"name": "荆棘岭十八公(树精)", "description": "松、柏、桧、竹等树木成精，以诗词会友，并无恶意"}, {"name": "杏仙", "description": "杏树精，欲与唐僧婚配"}], "dangerLevel": 2, "events": ["唐僧在荆棘岭与树精吟诗", "杏仙欲与唐僧成亲", "八戒将树精全部铲除"], "location": "荆棘岭木仙庵", "chapterRef": "第64回"},
        "小雷音遇难": {"demons": [{"name": "黄眉大王", "description": "弥勒佛面前司磬的黄眉童子，偷了人种袋和金钹下界，假扮如来佛建小雷音寺"}], "dangerLevel": 5, "events": ["唐僧误入小雷音寺拜假佛", "悟空被关入金钹", "二十八宿救出悟空"], "location": "小西天小雷音寺", "chapterRef": "第65回"},
        "诸天神遭困": {"demons": [{"name": "黄眉大王", "description": "人种袋可装天，所有天兵天将都被装入袋中"}], "dangerLevel": 5, "events": ["各路天兵天将均被人种袋收入", "弥勒佛前来收服黄眉童"], "location": "小西天", "chapterRef": "第66回"},
        "稀柿衕秽阻": {"demons": [{"name": "大蟒精", "description": "七绝山稀柿衕的巨蟒成精，虽不会说话但体型巨大"}], "dangerLevel": 2, "events": ["悟空和八戒合力杀死大蟒精", "八戒变成大猪拱开道路"], "location": "七绝山稀柿衕", "chapterRef": "第67回"},
        "朱紫国行医": {"demons": [{"name": "赛太岁(金毛犼)", "description": "观音菩萨的坐骑金毛犼，因朱紫国王年少时射伤孔雀明王的子女，被罚折凤三年"}], "dangerLevel": 3, "events": ["悟空揭皇榜为朱紫国王治病", "得知金圣宫娘娘被妖怪掳走"], "location": "朱紫国", "chapterRef": "第68-69回"},
        "拯救疲癃": {"demons": [{"name": "赛太岁(金毛犼)", "description": "同上"}], "dangerLevel": 3, "events": ["悟空降伏金毛犼救回金圣宫娘娘", "观音收回坐骑"], "location": "朱紫国麒麟山獬豸洞", "chapterRef": "第70回"},
        "降妖取后": {"demons": [{"name": "赛太岁", "description": "同上"}], "dangerLevel": 3, "events": ["紫金铃降伏赛太岁", "金圣宫娘娘回宫"], "location": "朱紫国", "chapterRef": "第71回"},
        "七情迷没": {"demons": [{"name": "七个蜘蛛精", "description": "盘丝洞的七个蜘蛛精，每日去濯垢泉洗澡"}], "dangerLevel": 2, "events": ["唐僧自去化斋误入盘丝洞", "蜘蛛精将唐僧捆住"], "location": "盘丝洞", "chapterRef": "第72回"},
        "多目遭伤": {"demons": [{"name": "百眼魔君(多目怪)", "description": "黄花观的蜈蚣精，胁下有千只眼，放出金光毒雾"}], "dangerLevel": 4, "events": ["多目怪千眼金光毒雾伤悟空", "毗蓝婆菩萨用绣花针收服"], "location": "黄花观", "chapterRef": "第73回"},
        "路阻狮驼": {"demons": [{"name": "青狮精", "description": "文殊菩萨坐骑"}, {"name": "白象精", "description": "普贤菩萨坐骑"}, {"name": "大鹏金翅雕", "description": "如来佛的舅舅，三大王之首"}], "dangerLevel": 5, "events": ["狮驼岭三妖控制狮驼国", "满城人全部被吃光"], "location": "狮驼岭狮驼洞", "chapterRef": "第74回"},
        "怪分三色": {"demons": [{"name": "青狮精、白象精、大鹏雕", "description": "同上"}], "dangerLevel": 5, "events": ["三妖结为兄弟占据狮驼山", "悟空变化探洞被识破装入阴阳二气瓶"], "location": "狮驼山", "chapterRef": "第75回"},
        "城里遇灾": {"demons": [{"name": "青狮、白象、大鹏", "description": "同上，大鹏最凶恶"}], "dangerLevel": 5, "events": ["师徒被三妖捉入狮驼城", "三妖要蒸吃唐僧", "悟空请如来佛亲临"], "location": "狮驼城", "chapterRef": "第76回"},
        "请佛收魔": {"demons": [{"name": "大鹏金翅雕、青狮、白象", "description": "如来佛亲自率文殊、普贤前来收服"}], "dangerLevel": 5, "events": ["如来佛亲临收服大鹏", "文殊普贤收回坐骑", "狮驼国妖怪一扫而空"], "location": "狮驼城", "chapterRef": "第77回"},
        "比丘救子": {"demons": [{"name": "白鹿精(国丈)", "description": "南极仙翁的坐骑白鹿下凡，与白面狐狸精勾结"}], "dangerLevel": 3, "events": ["比丘国国王要用一千小儿心肝做药引", "悟空揭穿国丈阴谋"], "location": "比丘国", "chapterRef": "第78回"},
        "辨认真邪": {"demons": [{"name": "白鹿精、白面狐狸精", "description": "南极仙翁坐骑和狐狸精"}], "dangerLevel": 3, "events": ["悟空揭穿假国丈", "南极仙翁收回白鹿", "狐狸精被打死"], "location": "比丘国", "chapterRef": "第79回"},
        "松林救怪": {"demons": [{"name": "金鼻白毛老鼠精(地涌夫人)", "description": "陷空山无底洞的老鼠精，在灵山偷吃如来的香花宝烛成精"}], "dangerLevel": 3, "events": ["唐僧在黑松林救下化作受难女子的老鼠精", "老鼠精在镇海禅林寺吃人"], "location": "黑松林", "chapterRef": "第80回"},
        "僧房卧病": {"demons": [{"name": "老鼠精", "description": "同上"}], "dangerLevel": 3, "events": ["唐僧在镇海寺生病", "老鼠精掳走唐僧"], "location": "镇海禅林寺", "chapterRef": "第81回"},
        "无底洞遭困": {"demons": [{"name": "金鼻白毛老鼠精", "description": "无底洞深不可测，老鼠精欲与唐僧成亲"}], "dangerLevel": 3, "events": ["悟空三探无底洞", "发现老鼠精拜李天王和哪吒牌位", "托塔天王和哪吒收服老鼠精"], "location": "陷空山无底洞", "chapterRef": "第82-83回"},
        "灭法国难行": {"demons": [{"name": "灭法国王(人)", "description": "灭法国国王发誓要杀一万个和尚，已经杀了九千九百九十六个"}], "dangerLevel": 2, "events": ["悟空半夜剃光国王和满朝文武的头发", "国王悔过改国名为钦法国"], "location": "灭法国", "chapterRef": "第84回"},
        "隐雾山遇魔": {"demons": [{"name": "豹子精(南山大王)", "description": "隐雾山折岳连环洞的豹子精，用假人头欺骗悟空"}], "dangerLevel": 3, "events": ["豹子精用假人头骗悟空说唐僧已被吃", "悟空八戒攻破连环洞"], "location": "隐雾山折岳连环洞", "chapterRef": "第85-86回"},
        "凤仙郡求雨": {"demons": [{"name": "无(天庭)", "description": "凤仙郡侯因推倒玉帝供桌喂狗，玉帝设米山、面山、金锁三道天罚"}], "dangerLevel": 2, "events": ["凤仙郡大旱三年", "悟空上天求玉帝降雨", "郡侯率全城行善赎罪后天降大雨"], "location": "凤仙郡", "chapterRef": "第87回"},
        "失落兵器": {"demons": [{"name": "黄狮精", "description": "玉华州竹节山九曲盘桓洞的黄狮精，偷走悟空八戒沙僧的兵器"}], "dangerLevel": 3, "events": ["黄狮精在半夜偷走金箍棒、九齿钯、降妖杖"], "location": "玉华州", "chapterRef": "第88回"},
        "会庆钉钯": {"demons": [{"name": "黄狮精", "description": "偷走兵器后举办钉钯宴"}], "dangerLevel": 3, "events": ["黄狮精设钉钯宴庆祝", "悟空八戒变成小妖混入", "夺回兵器烧毁洞穴"], "location": "竹节山九曲盘桓洞", "chapterRef": "第89回"},
        "竹节山遭难": {"demons": [{"name": "九灵元圣(九头狮)", "description": "太乙救苦天尊的坐骑，九头狮子，一声吼开九幽之门"}], "dangerLevel": 5, "events": ["九灵元圣不用兵器只用九个口将唐僧师徒全部擒住", "太乙天尊收回九灵元圣"], "location": "竹节山九曲盘桓洞", "chapterRef": "第90回"},
        "玄英洞受苦": {"demons": [{"name": "辟寒大王、辟暑大王、辟尘大王", "description": "三只犀牛精，假扮佛爷在金平府作怪"}], "dangerLevel": 4, "events": ["三只犀牛精在金平府冒充佛爷骗取酥合香油", "掳走唐僧"], "location": "金平府青龙山玄英洞", "chapterRef": "第91回"},
        "赶捉犀牛": {"demons": [{"name": "辟寒、辟暑、辟尘三犀牛精", "description": "三只犀牛精被四木禽星所克"}], "dangerLevel": 4, "events": ["四木禽星降伏三犀牛精", "将犀牛角献给天庭和金平府"], "location": "金平府", "chapterRef": "第92回"},
        "天竺招婚": {"demons": [{"name": "玉兔精", "description": "月宫中的玉兔下凡，用绣球砸中唐僧逼婚。原为报仇：天竺国公主原是蟾宫中素娥下凡，曾打过玉兔一掌"}], "dangerLevel": 3, "events": ["玉兔精在彩楼抛绣球砸中唐僧", "太阴星君收回玉兔"], "location": "天竺国布金禅寺", "chapterRef": "第93-95回"},
        "铜台府监禁": {"demons": [{"name": "寇洪(人)", "description": "并非妖怪。铜台府寇员外被强盗杀死，唐僧师徒被诬为凶手"}], "dangerLevel": 2, "events": ["唐僧师徒被诬陷为杀人犯入狱", "悟空施法戳穿强盗", "寇员外还魂"], "location": "铜台府", "chapterRef": "第96-97回"},
        "凌云渡脱胎": {"demons": [{"name": "无", "description": "凌云渡上接引佛祖的无底船，唐僧在此脱去凡胎"}], "dangerLevel": 1, "events": ["唐僧乘接引佛祖无底船过凌云渡", "凡胎从上游漂下", "脱胎换骨"], "location": "凌云渡", "chapterRef": "第98回"},
    }

    tribulations = []
    for entry in names:
        name = entry['name']
        idx = entry['index']

        if name in knowledge:
            info = knowledge[name]
            tribulation = {
                "id": idx,
                "order": idx,
                "name": name,
                "demons": info["demons"],
                "dangerLevel": info["dangerLevel"],
                "events": info["events"],
                "location": info["location"],
                "chapterRef": info["chapterRef"],
                # 坐标稍后根据地图计算
                "coordinates": {"x": 0, "y": 0}
            }
        else:
            # 未知难，使用模板
            tribulation = {
                "id": idx,
                "order": idx,
                "name": name,
                "demons": [{"name": "待考证", "description": "需要从西游记原文中查找"}],
                "dangerLevel": 1,
                "events": ["待补充"],
                "location": "待考证",
                "chapterRef": "待考证",
                "coordinates": {"x": 0, "y": 0}
            }

        tribulations.append(tribulation)

    # 添加第81难：通天河遇鼋湿经书
    tribulations.append({
        "id": 81,
        "order": 81,
        "name": "通天河遇鼋湿经书",
        "demons": [{"name": "白鼋(非妖怪)", "description": "老白鼋因唐僧忘了问如来他还有多少年寿，故将师徒连马带经书一起翻入通天河"}],
        "dangerLevel": 2,
        "events": [
            "八大金刚将师徒放回通天河西岸",
            "老白鼋驮师徒过河",
            "老白鼋问唐僧是否替问年寿",
            "唐僧无言以对",
            "老白鼋将师徒连经书一同翻入水中",
            "晒经石上晒干经书",
            "经书被石头粘破，不全"
        ],
        "location": "通天河",
        "chapterRef": "第99回",
        "coordinates": {"x": 0, "y": 0}
    })

    return tribulations


def compute_coordinates(tribulations):
    """
    计算每难在地图上的大致坐标。
    取经路线是从东(长安)到西(天竺)，大致呈东西走向带蜿蜒曲线。
    使用简单的正弦波路径。
    """
    import math

    n = len(tribulations)
    for i, t in enumerate(tribulations):
        # 从东到西，progress从0到1
        progress = i / (n - 1)

        # 从东(右)到西(左) - 如果是中式地图视图
        # x: 100(西安/东)→0(天竺/西)
        x = 100 - progress * 100

        # y: 加入蜿蜒路径，正弦波 + 整体向西南倾斜
        y = 50 + math.sin(progress * math.pi * 3) * 15 + progress * 25

        t["coordinates"] = {"x": round(x, 1), "y": round(y, 1)}

    return tribulations


def main():
    filepath = "西游记.txt"

    print("正在解析八十一难名称...")
    names = extract_tribulation_names(filepath)
    print(f"从原文解析出 {len(names)} 难")

    for n in names:
        print(f"  {n['index']:2d}. {n['name']}")

    print(f"\n正在构建结构化数据...")
    tribulations = build_tribulations_dataset(names)

    print(f"计算地图坐标...")
    tribulations = compute_coordinates(tribulations)

    output_path = "tribulations.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tribulations, f, ensure_ascii=False, indent=2)

    print(f"\n已生成 {output_path}，共 {len(tribulations)} 难")

    # 统计
    total_demons = sum(len(t['demons']) for t in tribulations)
    avg_danger = sum(t['dangerLevel'] for t in tribulations) / len(tribulations)
    print(f"妖怪总数: {total_demons}")
    print(f"平均危险等级: {avg_danger:.1f}/5")

    # 检查是否有待考证的条目
    unknowns = [t for t in tribulations if t['location'] == '待考证']
    if unknowns:
        print(f"\n⚠ 有 {len(unknowns)} 难需要手动考证:")
        for t in unknowns:
            print(f"  {t['id']}. {t['name']}")
    else:
        print(f"\n✓ 所有81难信息完整")


if __name__ == "__main__":
    main()
