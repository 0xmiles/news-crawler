#!/usr/bin/env python3
"""아키텍처 다이어그램 이미지 생성 스크립트"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

# 한글 폰트 설정
plt.rcParams['font.family'] = ['AppleGothic', 'Malgun Gothic', 'NanumGothic', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def create_architecture_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # 색상 정의
    orchestrator_color = '#4A90D9'
    agent_colors = ['#5CB85C', '#F0AD4E', '#D9534F', '#9B59B6']
    skill_color = '#3498DB'
    text_color = 'white'
    
    # Orchestrator 박스
    orchestrator = FancyBboxPatch(
        (1, 8), 12, 1.5,
        boxstyle="round,pad=0.05,rounding_size=0.2",
        facecolor=orchestrator_color,
        edgecolor='#2C5282',
        linewidth=2
    )
    ax.add_patch(orchestrator)
    ax.text(7, 8.9, 'Orchestrator', fontsize=16, fontweight='bold', 
            ha='center', va='center', color=text_color)
    ax.text(7, 8.4, '(워크플로우 조정)', fontsize=11, 
            ha='center', va='center', color=text_color)
    
    # 에이전트 박스 위치 및 정보
    agents = [
        {
            'name': 'PostSearcher',
            'items': ['• 웹 검색 (Claude)', '• 순위 매김'],
            'x': 1,
            'color': agent_colors[0]
        },
        {
            'name': 'BlogPlanner',
            'items': ['• 분석', '• 개요', '• 계획'],
            'x': 4.25,
            'color': agent_colors[1]
        },
        {
            'name': 'BlogWriter',
            'items': ['• 작성', '• 톤 적용', '• 다듬기'],
            'x': 7.5,
            'color': agent_colors[2]
        },
        {
            'name': 'BlogReviewer',
            'items': ['• 오탈자 검사', '• 말투 개선', '• 신뢰도 검증', '• 지식 학습'],
            'x': 10.75,
            'color': agent_colors[3]
        }
    ]
    
    box_width = 2.8
    box_height = 2.5
    
    for i, agent in enumerate(agents):
        # 에이전트 박스
        agent_box = FancyBboxPatch(
            (agent['x'], 4.5), box_width, box_height,
            boxstyle="round,pad=0.05,rounding_size=0.15",
            facecolor=agent['color'],
            edgecolor='#2C3E50',
            linewidth=2
        )
        ax.add_patch(agent_box)
        
        # 에이전트 이름
        ax.text(agent['x'] + box_width/2, 6.6, agent['name'], 
                fontsize=12, fontweight='bold', ha='center', va='center', color=text_color)
        
        # 에이전트 항목들
        for j, item in enumerate(agent['items']):
            ax.text(agent['x'] + 0.15, 6.1 - j*0.4, item, 
                    fontsize=9, ha='left', va='center', color=text_color)
        
        # Orchestrator에서 에이전트로 화살표
        arrow_x = agent['x'] + box_width/2
        ax.annotate('', xy=(arrow_x, 7), xytext=(arrow_x, 8),
                    arrowprops=dict(arrowstyle='->', color='#2C3E50', lw=2))
    
    # ToneLearner 박스
    tone_x = 5.5
    tone_y = 1.5
    tone_width = 3
    tone_height = 1.5
    
    tone_box = FancyBboxPatch(
        (tone_x, tone_y), tone_width, tone_height,
        boxstyle="round,pad=0.05,rounding_size=0.15",
        facecolor=skill_color,
        edgecolor='#1A5276',
        linewidth=2
    )
    ax.add_patch(tone_box)
    ax.text(tone_x + tone_width/2, 2.5, 'ToneLearner', 
            fontsize=12, fontweight='bold', ha='center', va='center', color=text_color)
    ax.text(tone_x + tone_width/2, 2.0, '(스킬)', 
            fontsize=10, ha='center', va='center', color=text_color)
    
    # BlogWriter에서 ToneLearner로 화살표
    ax.annotate('', xy=(tone_x + tone_width/2, 3), xytext=(agents[2]['x'] + box_width/2, 4.5),
                arrowprops=dict(arrowstyle='->', color='#2C3E50', lw=2))
    
    # assets 디렉토리 생성
    os.makedirs('assets', exist_ok=True)
    
    # 이미지 저장
    plt.tight_layout()
    plt.savefig('assets/architecture.png', dpi=150, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    print("✅ 아키텍처 다이어그램이 assets/architecture.png에 저장되었습니다.")

if __name__ == '__main__':
    create_architecture_diagram()
