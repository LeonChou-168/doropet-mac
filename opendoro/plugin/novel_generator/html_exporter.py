import os
from datetime import datetime
from typing import List, Optional
from .models import GameState, StoryMessage, MessageRole
from src.core.i18n import tr


class HTMLExporter:
    
    @staticmethod
    def _get_translated_template() -> str:
        """获取翻译后的 HTML 模板。"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: "Noto Serif SC", "Source Han Serif CN", "Microsoft YaHei", serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.8;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: #fff;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .meta-info {{
            background: #f8f9fa;
            padding: 20px 40px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .meta-info h2 {{
            font-size: 1.3em;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }}
        
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .meta-item {{
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        
        .meta-item .label {{
            font-size: 0.85em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        
        .meta-item .value {{
            font-size: 1.1em;
            color: #2c3e50;
            font-weight: 500;
        }}
        
        .characters-section {{
            padding: 20px 40px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .characters-section h2 {{
            font-size: 1.3em;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e74c3c;
        }}
        
        .character-card {{
            background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #e74c3c;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        .character-card .name {{
            font-size: 1.2em;
            color: #2c3e50;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        
        .character-card .details {{
            font-size: 0.95em;
            color: #7f8c8d;
        }}
        
        .story-content {{
            padding: 40px;
        }}
        
        .chapter {{
            margin-bottom: 40px;
        }}
        
        .chapter-title {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: #fff;
            padding: 20px 30px;
            border-radius: 8px;
            margin-bottom: 25px;
            text-align: center;
            font-size: 1.5em;
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
        }}
        
        .message {{
            background: #f8f9fa;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            border-left: 4px solid #95a5a6;
            position: relative;
        }}
        
        .message.narrator {{
            border-left-color: #3498db;
            background: linear-gradient(135deg, #f8f9fa 0%, #ecf0f1 100%);
        }}
        
        .message.character {{
            border-left-color: #e74c3c;
            background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
        }}
        
        .message .speaker {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        
        .message .speaker .name {{
            color: #2c3e50;
            font-weight: bold;
        }}
        
        .message .content {{
            font-size: 1.05em;
            color: #2c3e50;
            text-align: justify;
            white-space: pre-wrap;
        }}
        
        .choice-section {{
            background: #fff3cd;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }}
        
        .choice-section .label {{
            font-size: 0.9em;
            color: #856404;
            margin-bottom: 10px;
        }}
        
        .choice-section .choice-text {{
            font-size: 1em;
            color: #2c3e50;
            font-weight: 500;
        }}
        
        .effects {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px dashed #dee2e6;
        }}
        
        .effect {{
            font-size: 0.9em;
            padding: 5px 12px;
            border-radius: 20px;
            background: #e8f4f8;
            color: #2c3e50;
        }}
        
        .effect.positive {{
            background: #d4edda;
            color: #155724;
        }}
        
        .effect.negative {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .footer {{
            background: #2c3e50;
            color: #fff;
            padding: 30px;
            text-align: center;
            font-size: 0.9em;
        }}
        
        .footer .export-info {{
            opacity: 0.8;
            margin-top: 10px;
        }}
        
        @media print {{
            body {{
                background: #fff;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
                border-radius: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{story_title}</h1>
            <div class="subtitle">{world_name}</div>
        </div>
        
        <div class="meta-info">
            <h2>{story_overview_label}</h2>
            <div class="meta-grid">
                <div class="meta-item">
                    <div class="label">{protagonist_label}</div>
                    <div class="value">{protagonist_name}</div>
                </div>
                <div class="meta-item">
                    <div class="label">{chapter_label}</div>
                    <div class="value">{chapter_value}</div>
                </div>
                <div class="meta-item">
                    <div class="label">{currency_label}</div>
                    <div class="value">{currency_value}</div>
                </div>
                <div class="meta-item">
                    <div class="label">{export_time_label}</div>
                    <div class="value">{export_time}</div>
                </div>
            </div>
        </div>
        
        {characters_section}
        
        <div class="story-content">
            {story_messages}
        </div>
        
        <div class="footer">
            <div>{footer_generated_by}</div>
            <div class="export-info">{footer_exported_at}</div>
        </div>
    </div>
</body>
</html>'''
    
    @staticmethod
    def export_to_html(state: GameState, output_path: str, story_title: str = None) -> bool:
        try:
            html_content = HTMLExporter._generate_html(state, story_title)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    @staticmethod
    def _generate_html(state: GameState, story_title: str = None) -> str:
        if story_title is None:
            story_title = tr("galgame.html.untitled_story", default="未命名故事")
        
        protagonist_name = state.protagonist.name if state.protagonist else tr("galgame.html.unknown_protagonist", default="未知主角")
        world_name = state.world_setting.name if state.world_setting else tr("galgame.html.unknown_world", default="未知世界")
        
        characters_section = HTMLExporter._generate_characters_section(state)
        story_messages = HTMLExporter._generate_story_messages(state.messages)
        
        export_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        html_template = HTMLExporter._get_translated_template()
        
        chapter_label = tr("galgame.html.chapter_label", default="当前章节")
        chapter_value = tr("galgame.html.chapter_value", default="第 {} 章").format(state.chapter)
        
        currency_value = f"{state.currency} 💰"
        
        footer_generated_by = tr("galgame.html.footer_generated_by", default="由 DoroPet Galgame 生成")
        footer_exported_at = tr("galgame.html.footer_exported_at", default="导出于 {export_time}").format(export_time=export_time)
        
        html = html_template.format(
            title=f"{story_title} - Galgame Story",
            story_title=story_title,
            world_name=world_name,
            story_overview_label=tr("galgame.html.story_overview", default="故事概览"),
            protagonist_label=tr("galgame.html.protagonist_label", default="主角"),
            protagonist_name=protagonist_name,
            chapter_label=chapter_label,
            chapter_value=chapter_value,
            currency_label=tr("galgame.html.currency_label", default="金币"),
            currency_value=currency_value,
            export_time_label=tr("galgame.html.export_time_label", default="导出时间"),
            export_time=export_time,
            characters_section=characters_section,
            story_messages=story_messages,
            footer_generated_by=footer_generated_by,
            footer_exported_at=footer_exported_at
        )
        
        return html
    
    @staticmethod
    def _generate_characters_section(state: GameState) -> str:
        if not state.characters and not state.affections:
            return ""
        
        characters_title = tr("galgame.html.characters_title", default="角色信息")
        characters_html = ['<div class="characters-section">', f'<h2>{characters_title}</h2>']
        
        relationship_prefix = tr("galgame.html.relationship_prefix", default="关系: ")
        affection_suffix = tr("galgame.html.affection_suffix", default="好感度: {affection}/100")
        stranger = tr("galgame.html.stranger", default="陌生人")
        
        for char in state.characters:
            affection = 50
            relationship = stranger
            for aff in state.affections:
                if aff.character_name == char.name:
                    affection = aff.affection
                    relationship = aff.relationship
                    break
            
            details = f"{relationship_prefix}{relationship} | {affection_suffix.format(affection=affection)}"
            
            characters_html.append(f'''
            <div class="character-card">
                <div class="name">{char.name}</div>
                <div class="details">
                    {details}
                </div>
            </div>''')
        
        characters_html.append('</div>')
        return '\n'.join(characters_html)
    
    @staticmethod
    def _generate_story_messages(messages: List[StoryMessage]) -> str:
        no_content = tr("galgame.html.no_content", default="暂无故事内容")
        if not messages:
            return f'<p style="text-align: center; color: #7f8c8d;">{no_content}</p>'
        
        narrator_label = tr("galgame.html.narrator", default="旁白")
        choice_label = tr("galgame.html.choice", default="✦ 选择")
        
        html_parts = []
        current_chapter = 0
        
        for msg in messages:
            if msg.chapter_number != current_chapter:
                current_chapter = msg.chapter_number
                chapter_prefix = tr("galgame.status_bar.chapter", default="第{}章").format(current_chapter)
                if msg.chapter_name:
                    chapter_title = f"{chapter_prefix} · {msg.chapter_name}"
                else:
                    chapter_title = chapter_prefix
                html_parts.append(f'<div class="chapter"><div class="chapter-title">{chapter_title}</div>')
            
            message_class = "narrator"
            speaker = narrator_label
            
            if msg.role == MessageRole.CHARACTER and msg.character_name:
                message_class = "character"
                speaker = msg.character_name
            
            content = HTMLExporter._escape_html(msg.content)
            
            choice_html = ""
            if msg.selected_choice is not None and msg.choices:
                for choice in msg.choices:
                    if choice.id == msg.selected_choice:
                        choice_html = f'''
                        <div class="choice-section">
                            <div class="label">{choice_label}</div>
                            <div class="choice-text">{HTMLExporter._escape_html(choice.text)}</div>
                        </div>'''
                        break
            
            effects_html = ""
            if msg.affection_changes or msg.currency_change != 0:
                effects = []
                for char_name, change in msg.affection_changes.items():
                    effect_class = "positive" if change > 0 else "negative"
                    sign = "+" if change > 0 else ""
                    effects.append(f'<span class="effect {effect_class}">💕 {char_name} {sign}{change}</span>')
                
                if msg.currency_change != 0:
                    effect_class = "positive" if msg.currency_change > 0 else "negative"
                    sign = "+" if msg.currency_change > 0 else ""
                    effects.append(f'<span class="effect {effect_class}">💰 {sign}{msg.currency_change}</span>')
                
                effects_html = f'<div class="effects">{"".join(effects)}</div>'
            
            html_parts.append(f'''
            <div class="message {message_class}">
                <div class="speaker"><span class="name">{speaker}</span></div>
                <div class="content">{content}</div>
                {choice_html}
                {effects_html}
            </div>''')
        
        if current_chapter > 0:
            html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
