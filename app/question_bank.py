from __future__ import annotations

from dataclasses import dataclass, asdict
from random import sample


@dataclass
class Question:
    id: str
    stem: str
    options: list[str]
    answer: str
    knowledge_point: str
    explanation: str


QUESTION_BANK: list[Question] = [
    Question("Q001", "36 ÷ 4 = ?", ["A. 8", "B. 9", "C. 10", "D. 12"], "B", "除法计算", "36平均分成4份，每份是9。"),
    Question("Q002", "125 + 78 = ?", ["A. 193", "B. 203", "C. 213", "D. 215"], "B", "加法计算", "125加70是195，再加8是203。"),
    Question("Q003", "4 × 25 = ?", ["A. 90", "B. 95", "C. 100", "D. 105"], "C", "乘法计算", "4个25就是100。"),
    Question("Q004", "1米 = ? 厘米", ["A. 10", "B. 100", "C. 1000", "D. 60"], "B", "长度单位", "1米等于100厘米。"),
    Question("Q005", "0.6 元 = ? 角", ["A. 6", "B. 60", "C. 0.6", "D. 10"], "A", "小数与人民币", "1元=10角，所以0.6元=6角。"),
    Question("Q006", "一个长方形长8cm，宽3cm，周长是？", ["A. 11cm", "B. 24cm", "C. 22cm", "D. 16cm"], "C", "图形周长", "周长=(8+3)×2=22cm。"),
    Question("Q007", "600 ÷ 3 = ?", ["A. 20", "B. 200", "C. 300", "D. 180"], "B", "除法计算", "6百除以3等于2百。"),
    Question("Q008", "90 - 37 = ?", ["A. 43", "B. 53", "C. 57", "D. 63"], "B", "减法计算", "90减30是60，再减7是53。"),
    Question("Q009", "7.05 读作？", ["A. 七点五", "B. 七点零五", "C. 七五", "D. 七点五零"], "B", "小数读写", "小数点后每一位都要读出来。"),
    Question("Q010", "24时记时法中，下午3时是？", ["A. 13时", "B. 14时", "C. 15时", "D. 16时"], "C", "时间换算", "下午3时=15时。"),
    Question("Q011", "下面哪个数是偶数？", ["A. 37", "B. 49", "C. 58", "D. 73"], "C", "数的性质", "偶数能被2整除。"),
    Question("Q012", "45 × 2 = ?", ["A. 80", "B. 85", "C. 90", "D. 95"], "C", "乘法计算", "45的2倍是90。"),
    Question("Q013", "2000米 = ? 千米", ["A. 2", "B. 20", "C. 0.2", "D. 200"], "A", "长度单位", "1000米=1千米，所以2000米=2千米。"),
    Question("Q014", "980 + 20 = ?", ["A. 990", "B. 1000", "C. 1010", "D. 1020"], "B", "加法计算", "980加20凑整到1000。"),
    Question("Q015", "3个0.1相加是？", ["A. 0.03", "B. 0.3", "C. 3", "D. 0.13"], "B", "小数加法", "0.1+0.1+0.1=0.3。"),
    Question("Q016", "把20个苹果平均分给5人，每人几个？", ["A. 3", "B. 4", "C. 5", "D. 6"], "B", "除法应用", "20÷5=4。"),
    Question("Q017", "一个正方形边长6cm，周长是？", ["A. 12cm", "B. 18cm", "C. 24cm", "D. 36cm"], "C", "图形周长", "正方形周长=边长×4。"),
    Question("Q018", "9 × 9 = ?", ["A. 72", "B. 81", "C. 91", "D. 99"], "B", "乘法计算", "九九八十一。"),
    Question("Q019", "500毫升 + 500毫升 = ?", ["A. 1升", "B. 10升", "C. 0.1升", "D. 5升"], "A", "容量单位", "1000毫升=1升。"),
    Question("Q020", "72 ÷ 8 = ?", ["A. 7", "B. 8", "C. 9", "D. 10"], "C", "除法计算", "72除以8等于9。"),
    Question("Q021", "300 - 145 = ?", ["A. 145", "B. 155", "C. 165", "D. 175"], "B", "减法计算", "300减100是200，再减45是155。"),
    Question("Q022", "1小时20分 = ? 分", ["A. 60", "B. 70", "C. 80", "D. 120"], "C", "时间换算", "1小时=60分，60+20=80。"),
    Question("Q023", "0.9 > 0.89 吗？", ["A. 是", "B. 不是", "C. 相等", "D. 无法比较"], "A", "小数比较", "0.90大于0.89。"),
    Question("Q024", "28 + 19 = ?", ["A. 37", "B. 45", "C. 47", "D. 49"], "C", "加法计算", "28加20减1，等于47。"),
]


def generate_questions(count: int = 20, knowledge_points: list[str] | None = None) -> list[dict]:
    source = QUESTION_BANK
    if knowledge_points:
        source = [q for q in QUESTION_BANK if q.knowledge_point in knowledge_points]
    if len(source) < count:
        count = len(source)
    return [asdict(q) for q in sample(source, count)]
