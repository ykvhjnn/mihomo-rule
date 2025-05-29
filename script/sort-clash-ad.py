import sys
import asyncio

# 域名后缀黑名单（REMOVE_END）
REMOVE_END = {
    # 亚洲
    ".jp", ".kr", ".in", ".id", ".th", ".sg", ".my", ".ph", ".vn",
    ".pk", ".bd", ".lk", ".np", ".mn", ".uz", ".kz", ".kg", ".bt", ".mv", ".mm",
    # 欧洲
    ".uk", ".de", ".fr", ".it", ".es", ".ru", ".nl", ".be", ".ch", ".at", ".pl",
    ".cz", ".se", ".no", ".fi", ".dk", ".gr", ".pt", ".ie", ".hu", ".ro", ".bg",
    ".sk", ".si", ".lt", ".lv", ".ee", ".is", ".md", ".ua", ".by", ".am", ".ge",
    # 美洲
    ".us", ".ca", ".mx", ".br", ".ar", ".cl", ".co", ".pe", ".ve", ".uy", ".py",
    ".bo", ".ec", ".cr", ".pa", ".do", ".gt", ".sv", ".hn", ".ni", ".jm", ".cu",
    # 非洲
    ".za", ".eg", ".ng", ".ke", ".gh", ".tz", ".ug", ".dz", ".ma", ".tn", ".ly",
    ".ci", ".sn", ".zm", ".zw", ".ao", ".mz", ".bw", ".na", ".rw", ".mw", ".sd",
    # 大洋洲
    ".au", ".nz", ".fj", ".pg", ".sb", ".vu", ".nc", ".pf", ".ws", ".to", ".ki",
    ".tv", ".nr", ".as",
    # 中东
    ".sa", ".ae", ".ir", ".il", ".iq", ".tr", ".sy", ".jo", ".lb", ".om", ".qa",
    ".ye", ".kw", ".bh"
}

# 规则行黑名单关键词
FILTER_KEYWORDS = [
    "payload:", "rules:", "regexp", "IP-CIDR,", "DOMAIN-KEYWORD,", "PROCESS-NAME,",
    "IP-SUFFIX,", "GEOIP,", "GEOSITE,",
    "#", "!", "/", "【", "】", "[", "]", "$"
]

# 清理规则行的冗余字符
def clean_line(line: str) -> str:
    """清理行中的空格、无效符号，标准化原始字符串。"""
    for ch in " \"'|^":
        line = line.replace(ch, "")
    return line

# 判断行是否应该被过滤
def is_filtered_line(line: str) -> bool:
    if not line or "@@" in line:
        return True
    return any(keyword in line for keyword in FILTER_KEYWORDS)

# 提取有效域名
def extract_domain(line: str) -> str | None:
    """
    从规则行中提取有效域名。
    支持以下格式：
      - 'DOMAIN,domain'
      - 'DOMAIN-SUFFIX,domain'
      - '+.domain'
      - '*.domain'
      - '.domain'
      - 纯域名
    """
    line = clean_line(line.strip())
    if is_filtered_line(line):
        return None
    for prefix, offset in [
        ("DOMAIN,", 7),
        ("DOMAIN-SUFFIX,", 14),
        ("+.", 2),
        ("*.", 2),
        (".", 1),
        ("-DOMAIN,", 8),
        ("-DOMAIN-SUFFIX,", 15),
        ("-+.", 3),
        ("-*.", 3),
        ("-.", 2)
    ]:
        if line.startswith(prefix):
            return line[offset:]
    if "." in line:
        return line
    return None

# 判断域名是否需要被去除
def is_remove_end(domain: str) -> bool:
    return any(domain.endswith(suffix) for suffix in REMOVE_END)

# 只保留父域名
def filter_parent_domains(domains: set[str]) -> set[str]:
    sorted_domains = sorted(domains, key=lambda d: d[::-1])
    result = []
    for domain in sorted_domains:
        if not result or not domain.endswith("." + result[-1]):
            result.append(domain)
    return set(result)

# 异步读取文件，分块返回行列表
async def read_lines(file_path: str):
    with open(file_path, "r", encoding="utf8") as f:
        while True:
            lines = f.readlines(10000)
            if not lines:
                break
            yield lines

# 处理一块文件内容，提取合格域名
def process_chunk(chunk: list[str]) -> set[str]:
    result = set()
    for line in chunk:
        domain = extract_domain(line)
        if domain and not is_remove_end(domain):
            result.add(domain)
    return result

async def main():
    if len(sys.argv) < 2:
        print("请提供输入文件路径作为参数")
        return
    file_name = sys.argv[1]
    all_domains = set()
    async for chunk in read_lines(file_name):
        all_domains.update(process_chunk(chunk))
    filtered_domains = filter_parent_domains(all_domains)
    with open(file_name, "w", encoding="utf8") as f:
        for domain in sorted(filtered_domains):
            f.write(f"{domain}\n")
    print(f"处理完成，生成的规则总数为：{len(filtered_domains)}")

if __name__ == "__main__":
    asyncio.run(main())
