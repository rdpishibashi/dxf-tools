import ezdxf
import re

# DXFフォーマットコード除去用の正規表現
FORMAT_CODE_PATTERN = re.compile(r'(\\[A-Za-z0-9\.]+;)')

def extract_labels(dxf_file):
    """
    DXFファイルからラベル（MTEXTエンティティ）を抽出する
    
    Args:
        dxf_file: DXFファイルパス
        
    Returns:
        list: 抽出されたラベルのリスト
    """
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()

    labels = []

    # モデルスペース内のMTEXTのみ抽出
    for entity in msp:
        if entity.dxftype() == 'MTEXT':
            text = entity.dxf.text
            cleaned = FORMAT_CODE_PATTERN.sub('', text)
            cleaned = cleaned.replace('\\P', ' ').strip()
            if cleaned:
                labels.append(cleaned)

    return labels