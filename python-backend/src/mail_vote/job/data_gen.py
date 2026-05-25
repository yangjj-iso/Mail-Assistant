"""高质量合成数据生成器：生成覆盖国内大厂实习/秋招/春招全流程的 NER 标注数据和分类训练数据。"""

from __future__ import annotations

import json
import random
import csv
from pathlib import Path
from typing import List, Dict

# ============================================================
# 实体词典 - 覆盖国内主流互联网/科技/金融公司
# ============================================================

COMPANIES = [
    # 互联网大厂
    "字节跳动", "腾讯", "阿里巴巴", "百度", "美团", "京东", "华为", "小米",
    "网易", "快手", "滴滴", "拼多多", "蚂蚁集团", "哔哩哔哩", "知乎", "小红书",
    "得物", "货拉拉", "携程", "去哪儿", "饿了么", "顺丰科技", "SHEIN",
    # 新兴科技
    "大疆创新", "商汤科技", "旷视科技", "寒武纪", "地平线", "云从科技",
    "第四范式", "思谋科技", "智谱AI", "月之暗面", "MiniMax", "百川智能",
    # 汽车/硬件
    "蔚来汽车", "理想汽车", "小鹏汽车", "比亚迪", "宁德时代", "中芯国际",
    "联想集团", "OPPO", "vivo", "荣耀", "传音控股",
    # 游戏
    "米哈游", "莉莉丝", "三七互娱", "网易游戏", "腾讯游戏", "叠纸游戏",
    # 外企
    "微软", "谷歌", "亚马逊", "苹果", "英特尔", "英伟达", "AMD",
    "高通", "博通", "甲骨文", "SAP", "Shopee", "Grab",
    # 金融
    "高盛", "摩根士丹利", "中金公司", "招商银行", "平安科技", "蚂蚁金服",
    "陆金所", "微众银行", "京东数科",
    # 国企/研究所
    "中国移动", "中国电信", "中国联通", "海康威视", "科大讯飞", "中兴通讯",
]

POSITIONS_INTERN = [
    "后端开发实习生", "前端开发实习生", "算法实习生", "数据分析实习生",
    "产品经理实习生", "测试开发实习生", "运维开发实习生", "Java开发实习生",
    "Python开发实习生", "Go开发实习生", "C++开发实习生", "iOS开发实习生",
    "Android开发实习生", "全栈开发实习生", "机器学习实习生", "NLP算法实习生",
    "计算机视觉实习生", "大数据开发实习生", "云计算实习生", "安全工程实习生",
    "推荐算法实习生", "搜索算法实习生", "广告算法实习生", "风控算法实习生",
    "数据挖掘实习生", "图形渲染实习生", "游戏开发实习生", "嵌入式开发实习生",
    "FPGA开发实习生", "芯片验证实习生", "SRE实习生", "DevOps实习生",
]

POSITIONS_FULLTIME = [
    "后端开发工程师", "前端开发工程师", "算法工程师", "数据分析师",
    "产品经理", "测试工程师", "运维工程师", "Java开发工程师", "Python开发工程师",
    "Go开发工程师", "C++开发工程师", "iOS开发工程师", "Android开发工程师",
    "全栈工程师", "机器学习工程师", "NLP工程师", "计算机视觉工程师",
    "大数据工程师", "云计算工程师", "安全工程师", "架构师",
    "推荐系统工程师", "搜索工程师", "广告系统工程师", "风控工程师",
    "数据工程师", "DevOps工程师", "SRE工程师", "嵌入式开发工程师",
    "FPGA工程师", "芯片设计工程师", "游戏服务端开发", "游戏客户端开发",
    "音视频开发工程师", "图形渲染工程师", "区块链工程师", "量化开发工程师",
]

DEPARTMENTS = [
    "飞书", "抖音", "TikTok", "今日头条", "懂车帝", "番茄小说",
    "微信事业群", "PCG", "IEG", "TEG", "CSIG", "CDG",
    "淘天集团", "阿里云", "菜鸟", "本地生活", "国际数字商业",
    "智能驾驶", "自动驾驶", "智能座舱", "基础架构", "中间件",
    "搜索技术", "推荐技术", "广告技术", "风控平台", "数据平台",
    "AI Lab", "AI平台", "大模型团队", "基础研究", "应用研究",
]

ROUNDS = [
    "一面", "二面", "三面", "HR面", "终面", "主管面",
    "技术一面", "技术二面", "技术三面", "交叉面", "加面",
]

ROUNDS_WRITTEN = ["笔试", "在线测评", "编程测试", "技术笔试", "综合测评"]

LOCATIONS_ONSITE = [
    "北京市海淀区中关村软件园", "北京市海淀区西二旗", "北京市朝阳区望京",
    "北京市朝阳区酒仙桥", "北京市海淀区知春路",
    "上海市浦东新区张江高科", "上海市徐汇区漕河泾", "上海市闵行区虹桥",
    "上海市杨浦区五角场", "上海市长宁区",
    "深圳市南山区科技园", "深圳市南山区后海", "深圳市福田区",
    "深圳市宝安区", "深圳市龙岗区坂田",
    "杭州市余杭区未来科技城", "杭州市西湖区", "杭州市滨江区",
    "广州市天河区", "广州市海珠区琶洲",
    "成都市高新区天府软件园", "武汉市东湖高新区光谷",
    "南京市雨花台区软件谷", "西安市高新区", "合肥市高新区",
]

LOCATIONS_ONLINE = [
    "线上（腾讯会议）", "线上（飞书视频）", "线上（Zoom）",
    "线上（Teams）", "线上（钉钉）", "线上（牛客面试）",
    "视频面试（飞书）", "视频面试（腾讯会议）", "视频面试（Zoom）",
    "远程面试", "电话面试",
]

# ============================================================
# 时间生成
# ============================================================

TIME_TEMPLATES = [
    "2026年{m}月{d}日 {h}:{mi}",
    "2025年{m}月{d}日 {h}:{mi}",
    "{m}月{d}日（周{w}）{h}:{mi}",
    "{m}月{d}日 {h}:{mi}",
    "{m}/{d} {h}:{mi}",
    "{m}月{d}号下午{h2}点",
    "{m}月{d}号上午{h3}点",
    "{m}月{d}号 {h}:{mi}",
    "本周{w2} {h}:{mi}",
    "下周{w2} {h}:{mi}",
    "{m}月{d}日（{w2}）下午{h2}:{mi}",
    "{m}月{d}日（{w2}）上午{h3}:{mi}",
    "2026-{m:02d}-{d:02d} {h}:{mi}",
    "2025-{m:02d}-{d:02d} {h}:{mi}",
]

WEEKDAYS = ["一", "二", "三", "四", "五"]
WEEKDAYS2 = ["周一", "周二", "周三", "周四", "周五"]


def _random_time() -> str:
    fmt = random.choice(TIME_TEMPLATES)
    m = random.randint(3, 11)
    d = random.randint(1, 28)
    h = random.randint(9, 18)
    mi = random.choice(["00", "30", "15", "45"])
    h2 = random.randint(1, 6)
    h3 = random.randint(9, 11)
    w = random.choice(WEEKDAYS)
    w2 = random.choice(WEEKDAYS2)
    return fmt.format(m=m, d=d, h=h, mi=mi, h2=h2, h3=h3, w=w, w2=w2)


# ============================================================
# 邮件模板 - 面试邀约（最丰富，覆盖各种真实格式）
# ============================================================

INTERVIEW_TEMPLATES = [
    # 标准格式 - 完整信息
    "您好，恭喜您通过{company}的{position}岗位简历筛选，{round}安排在{time}，地点：{location}。请准时参加。",
    "{company}邀请您参加{position}的{round}，时间：{time}，地点：{location}。如有问题请回复此邮件。",
    "尊敬的候选人，您申请的{company}{position}职位已进入{round}环节，面试时间为{time}，面试地点：{location}。",
    "通知：{company}{position}岗位{round}定于{time}进行，地址：{location}，请提前10分钟到达。",
    "您好！{company}HR通知您，{position}的{round}已安排，时间{time}，{location}，届时请携带简历。",
    "面试邀请：{company}诚邀您参加{position}{round}，{time}，{location}。期待您的到来！",
    # 字节跳动风格
    "{company}诚邀你参加{company}校园招聘-{position}岗位的面试，感谢你的耐心等待。\n\n【面试信息】\n面试形式：视频面试\n面试时间：{time}\n面试轮次：{round}\n面试地点：{location}",
    "Hi，你好！你已通过{company}{position}的简历筛选，现邀请你参加{round}。\n面试时间：{time}\n面试方式：{location}\n请提前5分钟进入面试间。",
    # 腾讯风格
    "恭喜您通过{company}{position}岗位的前序面试环节！现通知您参加{round}。\n\n面试时间：{time}\n面试地点：{location}\n温馨提示：请携带身份证和学生证。",
    "【{company}校招】{position}岗位{round}通知\n\n亲爱的同学：\n恭喜您进入{round}环节！\n时间：{time}\n地点：{location}\n请准时参加，如需改期请提前联系HR。",
    # 阿里风格
    "同学你好，恭喜你通过{company}{position}的面试评估，现安排{round}如下：\n时间：{time}\n地点：{location}\n面试官将通过视频/电话联系你，请保持通讯畅通。",
    "【{company}招聘】面试邀约通知\n\n你好，你申请的{position}岗位已安排{round}：\n- 时间：{time}\n- 地点：{location}\n\n祝面试顺利！",
    # 华为风格
    "尊敬的应聘者：\n感谢您应聘{company}{position}岗位。经初步评估，现邀请您参加{round}。\n面试时间：{time}\n面试地点：{location}\n请务必准时到达。",
    "【{company}校园招聘】面试通知\n\n您好，您申请的{position}职位已通过筛选，{round}安排如下：\n时间：{time}\n地点：{location}\n如有疑问请致电HR。",
    # 美团风格
    "Hi~恭喜你通过{company}{position}的简历评估！\n{round}信息：\n时间：{time}\n地点：{location}\n期待与你见面！",
    # 通用详细格式
    "面试通知\n\n候选人您好：\n\n您投递的{company}{position}岗位已进入面试阶段。\n\n面试详情：\n- 面试轮次：{round}\n- 面试时间：{time}\n- 面试地点：{location}\n\n注意事项：\n1. 请提前10分钟到达\n2. 携带个人简历一份\n3. 如需改期请提前24小时联系",
    "【面试邀约】{company}-{position}\n\n同学你好！\n\n经过评估，你已进入{round}环节。\n\n面试安排：\n时间：{time}\n地点：{location}\n\n温馨提示：面试时长约45-60分钟，请合理安排时间。",
    # 简短通知
    "{company}{position}{round}：{time}，{location}。",
    "你好，{company}{round}已安排：{time}，{location}，岗位{position}。",
    "{round}通知：{company}{position}，{time}在{location}进行面试。",
    # 带部门信息
    "{company}诚邀您参加{position}（{dept}）的{round}，时间：{time}，地点：{location}。",
    "您好，{company}{dept}团队邀请您参加{position}岗位的{round}，面试时间{time}，地点{location}。",
    # 实习专用
    "【实习面试】{company}{position}岗位{round}通知\n时间：{time}\n地点：{location}\n实习时长要求：至少3个月，每周4天以上。",
    "Hi同学，{company}暑期实习-{position}的{round}已安排：\n{time}\n{location}\n期待你的表现！",
    # 新增：覆盖更多边界情况
    "很高兴通知您，{company}{position}岗位的{round}定于{time}，{location}。",
    "诚邀您参加{company}的{round}，岗位：{position}，时间：{time}，地点：{location}。",
    "【{company}】很高兴通知您，{position}岗位的{round}已安排在{time}，{location}。",
]

# ============================================================
# 邮件模板 - 投递确认
# ============================================================

APPLIED_TEMPLATES = [
    "您好，您投递的{company}{position}岗位已收到，我们将尽快审核您的简历。",
    "感谢您申请{company}的{position}职位，您的简历已成功提交，请耐心等待后续通知。",
    "投递确认：您已成功申请{company}{position}岗位，HR将在3-5个工作日内回复。",
    "您好，{company}已收到您{position}岗位的求职申请，感谢您的关注。",
    "申请确认函：您对{company}{position}的申请已记录，祝您求职顺利。",
    "【{company}校招】简历投递成功通知\n\n同学你好：\n你投递的{position}岗位简历已成功提交。我们将在5个工作日内完成简历筛选，届时会通过邮件通知你后续安排。",
    "感谢你对{company}的关注！你申请的{position}职位已进入简历评估阶段，请保持手机畅通。",
    "【投递成功】{company}-{position}\n\n你好，你的简历已成功投递至{company}{position}岗位。简历筛选结果将在1-2周内通知。",
    "您好，感谢您投递{company}{position}（{dept}）岗位，我们已收到您的申请材料。",
    "Hi，你的{company}校招申请（{position}）已提交成功，请关注后续邮件通知。",
    "【{company}】投递确认\n\n亲爱的同学：\n感谢你申请{company}{position}岗位。你的简历正在评估中，请耐心等待。\n\n{company}招聘团队",
    "你好！你已成功申请{company}2026届校招-{position}岗位，祝你好运！",
]

# ============================================================
# 邮件模板 - 笔试通知
# ============================================================

WRITTEN_TEST_TEMPLATES = [
    "您好，{company}邀请您参加{position}岗位的在线笔试，时间：{time}，请登录指定平台完成。",
    "笔试通知：{company}{position}笔试安排在{time}，时长120分钟，请提前准备好网络环境。",
    "{company}{position}在线测评通知：请于{time}前完成在线笔试，链接将在考试前发送。",
    "您好，恭喜进入{company}{position}笔试环节，笔试时间{time}，请注意查收后续邮件。",
    "【{company}校招笔试通知】\n\n同学你好：\n恭喜你通过{position}岗位的简历筛选！现邀请你参加在线笔试。\n\n笔试时间：{time}\n笔试时长：120分钟\n笔试平台：牛客网\n\n注意事项：\n1. 请提前10分钟登录\n2. 确保网络稳定\n3. 禁止切屏",
    "Hi，{company}{position}的在线编程测试已开放：\n时间：{time}\n平台：赛码网\n题目类型：算法+系统设计\n请按时完成。",
    "【笔试邀请】{company}-{position}\n\n你好，你已通过简历筛选，现邀请参加笔试：\n时间：{time}\n形式：在线编程\n时长：2小时\n\n请提前准备好IDE环境。",
    "{company}2026校招{position}岗位笔试通知：\n笔试时间：{time}\n笔试形式：在线（牛客）\n包含：编程题3道+选择题20道",
    "通知：{company}{position}技术笔试定于{time}进行，请登录赛码网完成，时长90分钟。",
    "【{company}】{position}在线测评\n\n你好，请于{time}完成{company}的在线能力测评，测评链接已发送至你的手机。",
    "恭喜！你已进入{company}{position}笔试环节。\n笔试时间：{time}\n笔试内容：数据结构与算法\n祝你取得好成绩！",
]

# ============================================================
# 邮件模板 - Offer
# ============================================================

OFFER_TEMPLATES = [
    "恭喜您！{company}正式向您发出{position}岗位的录用通知(Offer)，期待您的加入！",
    "Offer Letter：经过综合评估，{company}决定录用您为{position}，薪资待遇详见附件。",
    "您好，很高兴通知您已通过{company}{position}的全部面试流程，现正式发出录用意向。",
    "录用通知：{company}诚挚邀请您加入我们的团队，担任{position}一职。",
    "【{company}】录用通知书\n\n亲爱的同学：\n\n恭喜你！经过层层选拔，你已成功通过{company}{position}岗位的全部面试环节。\n\n我们非常高兴地向你发出正式录用通知（Offer）。\n\n入职时间：{time}\n工作地点：{location}\n\n请在收到本邮件后3个工作日内确认是否接受。",
    "Hi，恭喜你拿到{company}的Offer！\n\n岗位：{position}\n工作地点：{location}\n入职日期：{time}\n\n请尽快确认接受意向，期待你的加入！",
    "【Offer通知】{company}-{position}\n\n同学你好：\n\n经过综合评估，我们很高兴通知你已通过{company}{position}岗位的全部面试。现正式向你发出录用意向。\n\n详细信息请查看附件中的Offer Letter。\n\n{company}人力资源部",
    "恭喜！{company}{position}（{dept}）岗位Offer已发出，工作地点{location}，请查收附件。",
    "你好，{company}向你发出{position}的实习Offer！\n实习地点：{location}\n开始时间：{time}\n实习时长：3-6个月\n期待你的确认！",
    "【录用通知】\n\n尊敬的候选人：\n\n经{company}面试委员会综合评定，现正式通知您已被录用为{position}。\n\n报到时间：{time}\n报到地点：{location}\n\n请携带相关证件按时报到。",
]

# ============================================================
# 邮件模板 - 拒信
# ============================================================

REJECTED_TEMPLATES = [
    "很遗憾通知您，经过慎重考虑，{company}{position}岗位未能与您达成匹配，感谢您的参与。",
    "您好，感谢您参加{company}{position}的面试，遗憾的是本次未能通过，祝您前程似锦。",
    "通知：您申请的{company}{position}职位，经评估后暂不符合当前需求，欢迎未来再次申请。",
    "尊敬的候选人，{company}{position}岗位竞争激烈，很遗憾本次未能录用，感谢您的时间。",
    "【{company}】面试结果通知\n\n同学你好：\n\n感谢你参加{company}{position}岗位的面试。经过综合评估，很遗憾本次未能通过。\n\n我们非常感谢你在面试中展现的专业能力，希望未来有机会再次合作。\n\n祝你求职顺利！\n{company}招聘团队",
    "Hi，感谢你对{company}的关注和参与。经过评估，{position}岗位本次暂未匹配成功。我们已将你的简历纳入人才库，后续如有合适机会会优先联系你。",
    "您好，{company}{position}（{dept}）岗位面试结果已出，很遗憾未能通过本轮评估。感谢您的时间和努力。",
    "【面试结果】{company}-{position}\n\n同学你好，感谢你参加我们的面试。经过慎重考虑，本次未能给出offer，但你的表现给我们留下了深刻印象。祝一切顺利！",
    "遗憾通知：{company}{position}岗位经综合评定，本次未能录用。感谢你的参与，祝前程似锦。",
    "你好，{company}校招{position}岗位面试已结束，很遗憾本次未能通过。欢迎关注我们的社招机会。",
]

# ============================================================
# 非求职邮件模板（负样本）
# ============================================================

NOT_JOB_TEMPLATES = [
    "您的{company}账号于{time}在新设备登录，如非本人操作请立即修改密码。",
    "您在{company}的订单已发货，预计3-5天送达，请注意查收。",
    "【{company}】您的验证码是{code}，5分钟内有效，请勿泄露。",
    "{company}双十一大促开始啦！全场满300减50，活动截止{time}。",
    "您关注的{company}论坛帖子有新回复，点击查看详情。",
    "【{company}通知】系统将于{time}进行维护升级，届时服务暂停。",
    "您的{company}会员即将到期，续费享8折优惠。",
    "{company}周报：本周团队完成了3个迭代，详情请查看附件。",
    "【{company}】您的快递已签收，如有问题请联系客服。",
    "尊敬的用户，{company}新版本已发布，立即更新体验新功能。",
    "您在{company}的评论收到了3条回复，快来看看吧。",
    "【安全提醒】{company}检测到您的账号存在异常，请尽快验证。",
    "{company}邀请您参加用户满意度调查，完成可获得优惠券。",
    "您订阅的{company}技术博客有新文章发布：《微服务架构实践》。",
    "【{company}】您的退款申请已处理，金额将在1-3个工作日内退回。",
    "Hi，{company}社区本周热门话题：如何提升代码质量？",
    "您的{company}云服务器即将到期，请及时续费避免数据丢失。",
    "【通知】{company}将于{time}举办线上技术分享会，欢迎参加。",
    "{company}年度账单已生成，点击查看您的消费详情。",
    "您在{company}的文章《Python最佳实践》获得了50个点赞。",
]

# ============================================================
# 分词与标注
# ============================================================


def _tokenize(text: str) -> List[str]:
    """字符级分词，英文单词和数字保持完整。"""
    tokens: List[str] = []
    buf = ""
    for ch in text:
        if ch.isascii() and (ch.isalpha() or ch.isdigit() or ch == ':'):
            buf += ch
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            if ch.strip():
                tokens.append(ch)
    if buf:
        tokens.append(buf)
    return tokens


def _label_tokens(tokens: List[str], entities: Dict[str, str]) -> List[str]:
    """对 tokens 进行 BIO 标注。"""
    labels = ["O"] * len(tokens)

    for ent_type, ent_value in entities.items():
        if not ent_value:
            continue
        ent_tokens = _tokenize(ent_value)
        if not ent_tokens:
            continue
        for i in range(len(tokens) - len(ent_tokens) + 1):
            if tokens[i:i + len(ent_tokens)] == ent_tokens:
                if labels[i] != "O":
                    continue
                labels[i] = f"B-{ent_type}"
                for j in range(1, len(ent_tokens)):
                    labels[i + j] = f"I-{ent_type}"
                break
    return labels


# ============================================================
# NER 数据生成
# ============================================================

# 笔试NER模板（包含ROUND实体）
WRITTEN_TEST_NER_TEMPLATES = [
    "{company}通知您参加{position}岗位的{round}，时间：{time}，请登录指定平台完成。",
    "{round}通知：{company}{position}{round}安排在{time}，时长120分钟。",
    "{company}{position}的{round}已开放：时间：{time}，平台：牛客网。",
    "您好，恭喜进入{company}{position}{round}环节，{round}时间{time}。",
    "【{company}校招{round}通知】{position}岗位{round}时间：{time}。",
    "{company}2026校招{position}岗位{round}通知：{round}时间：{time}。",
    "通知：{company}{position}技术{round}定于{time}进行。",
    "恭喜！你已进入{company}{position}{round}环节。{round}时间：{time}。",
    # 新增：覆盖更多边界情况
    "诚邀您参加{company}的{round}，时间：{time}，{location}。",
    "诚邀您参加{company}{position}岗位的{round}，时间：{time}。",
    "很高兴通知您，{company}{position}岗位的{round}定于{time}，{location}。",
    "【{company}】诚邀您参加{position}的{round}，时间{time}。",
]


def generate_ner_data(n_samples: int = 1200, seed: int = 42) -> List[Dict]:
    """生成 NER 标注数据，覆盖面试邀约和笔试的各种格式。"""
    random.seed(seed)
    samples: List[Dict] = []

    # 80% 面试模板，20% 笔试模板
    n_interview = int(n_samples * 0.8)
    n_written = n_samples - n_interview

    # 面试数据
    for _ in range(n_interview):
        company = random.choice(COMPANIES)
        is_intern = random.random() < 0.4
        position = random.choice(POSITIONS_INTERN if is_intern else POSITIONS_FULLTIME)
        round_ = random.choice(ROUNDS)
        is_online = random.random() < 0.5
        location = random.choice(LOCATIONS_ONLINE if is_online else LOCATIONS_ONSITE)
        time_ = _random_time()
        dept = random.choice(DEPARTMENTS)

        template = random.choice(INTERVIEW_TEMPLATES)
        text = template.format(
            company=company, position=position,
            round=round_, time=time_, location=location,
            dept=dept,
        )
        tokens = _tokenize(text)
        entities = {
            "COMPANY": company,
            "POSITION": position,
            "ROUND": round_,
            "TIME": time_,
            "LOCATION": location,
        }
        labels = _label_tokens(tokens, entities)
        samples.append({"tokens": tokens, "labels": labels})

    # 笔试数据
    for _ in range(n_written):
        company = random.choice(COMPANIES)
        is_intern = random.random() < 0.4
        position = random.choice(POSITIONS_INTERN if is_intern else POSITIONS_FULLTIME)
        round_ = random.choice(ROUNDS_WRITTEN)  # 使用笔试轮次
        time_ = _random_time()
        is_online = random.random() < 0.5
        location = random.choice(LOCATIONS_ONLINE if is_online else LOCATIONS_ONSITE)

        template = random.choice(WRITTEN_TEST_NER_TEMPLATES)
        text = template.format(
            company=company, position=position,
            round=round_, time=time_, location=location,
        )
        tokens = _tokenize(text)
        entities = {
            "COMPANY": company,
            "POSITION": position,
            "ROUND": round_,
            "TIME": time_,
            "LOCATION": location,
        }
        labels = _label_tokens(tokens, entities)
        samples.append({"tokens": tokens, "labels": labels})

    random.shuffle(samples)
    return samples


# ============================================================
# 分类数据生成
# ============================================================


def generate_classifier_data(n_per_class: int = 200, seed: int = 42) -> List[Dict]:
    """生成求职检测+阶段分类训练数据。"""
    random.seed(seed)
    samples: List[Dict] = []

    stage_templates = {
        "applied": APPLIED_TEMPLATES,
        "written_test": WRITTEN_TEST_TEMPLATES,
        "interview": INTERVIEW_TEMPLATES,
        "offer": OFFER_TEMPLATES,
        "rejected": REJECTED_TEMPLATES,
    }

    for stage, templates in stage_templates.items():
        for _ in range(n_per_class):
            company = random.choice(COMPANIES)
            is_intern = random.random() < 0.4
            position = random.choice(POSITIONS_INTERN if is_intern else POSITIONS_FULLTIME)
            round_ = random.choice(ROUNDS)
            is_online = random.random() < 0.5
            location = random.choice(LOCATIONS_ONLINE if is_online else LOCATIONS_ONSITE)
            time_ = _random_time()
            dept = random.choice(DEPARTMENTS)
            template = random.choice(templates)
            text = template.format(
                company=company, position=position,
                round=round_, time=time_, location=location,
                dept=dept,
            )
            samples.append({"text": text, "label": stage, "is_job": True})

    for _ in range(n_per_class * 2):
        company = random.choice(COMPANIES)
        time_ = _random_time()
        code = str(random.randint(100000, 999999))
        template = random.choice(NOT_JOB_TEMPLATES)
        text = template.format(company=company, time=time_, code=code)
        samples.append({"text": text, "label": "not_job", "is_job": False})

    random.shuffle(samples)
    return samples


# ============================================================
# 保存数据
# ============================================================


def save_ner_data(output_dir: Path, n_samples: int = 1200, seed: int = 42) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = generate_ner_data(n_samples, seed)

    train_split = int(len(samples) * 0.85)
    train_path = output_dir / "ner_train.jsonl"
    test_path = output_dir / "ner_test.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for s in samples[:train_split]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(test_path, "w", encoding="utf-8") as f:
        for s in samples[train_split:]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"NER data saved: {train_split} train, {len(samples) - train_split} test")
    return output_dir


def save_classifier_data(output_dir: Path, n_per_class: int = 200, seed: int = 42) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = generate_classifier_data(n_per_class, seed)

    train_split = int(len(samples) * 0.85)
    train_path = output_dir / "job_cls_train.csv"
    test_path = output_dir / "job_cls_test.csv"

    for path, data in [(train_path, samples[:train_split]), (test_path, samples[train_split:])]:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "label", "is_job"])
            writer.writeheader()
            writer.writerows(data)

    print(f"Classifier data saved: {train_split} train, {len(samples) - train_split} test")
    return output_dir


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent.parent.parent / "data" / "job"
    print(f"Generating data to {out}")
    save_ner_data(out, n_samples=1200)
    save_classifier_data(out, n_per_class=200)
    print("Done.")
