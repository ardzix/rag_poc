"""
Helper functions untuk chat service
"""


def detect_chart_needed(message: str) -> bool:
    """
    Deteksi otomatis apakah user meminta chart/visualisasi
    berdasarkan kata kunci dalam message
    
    Args:
        message: Pesan dari user
    
    Returns:
        True jika terdeteksi perlu chart, False jika tidak
    """
    # Normalize message
    msg_lower = message.lower()
    
    # Keywords yang mengindikasikan user minta chart/visualisasi
    chart_keywords = [
        'chart', 'grafik', 'graph',
        'visualisasi', 'visualkan', 'visualisasikan',
        'diagram', 'plot',
        'perbandingan', 'bandingkan',
        'tren', 'trend',
        'tampilkan data', 'tampilkan angka',
        'buatkan chart', 'buatkan grafik',
        'lihat chart', 'lihat grafik',
        'perkembangan',
        'vs', 'versus',
        'bar chart', 'line chart', 'pie chart',
    ]
    
    # Cek apakah ada keyword yang match
    for keyword in chart_keywords:
        if keyword in msg_lower:
            return True
    
    return False
