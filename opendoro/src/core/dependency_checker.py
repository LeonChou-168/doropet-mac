import sys
import os
import re
import subprocess
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from src.core.platform_paths import get_app_root, is_macos, is_windows


@dataclass
class DependencyMismatch:
    package_name: str
    required_version: str
    installed_version: str
    operator: str


@dataclass
class DependencyCheckResult:
    success: bool
    mismatches: List[DependencyMismatch]
    missing_packages: List[str]
    error_message: Optional[str] = None


def parse_requirements_file(requirements_path: str) -> Dict[str, Tuple[str, str]]:
    """
    解析 requirements.txt 文件，返回包名和版本要求的字典
    返回格式: {package_name: (operator, version)}
    """
    requirements = {}
    
    if not os.path.exists(requirements_path):
        return requirements
    
    with open(requirements_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*([=<>!~]+)\s*([^\s;#]+)', line)
            if match:
                package_name = match.group(1).lower()
                operator = match.group(2)
                version = match.group(3)
                requirements[package_name] = (operator, version)
            elif re.match(r'^[a-zA-Z0-9_-]+$', line):
                package_name = line.lower()
                requirements[package_name] = ('', '')
    
    return requirements


def get_installed_version(package_name: str) -> Optional[str]:
    """
    获取已安装包的版本
    """
    try:
        if sys.version_info >= (3, 8):
            from importlib.metadata import version, PackageNotFoundError
            try:
                normalized_name = package_name.replace('-', '_').lower()
                return version(normalized_name)
            except PackageNotFoundError:
                return None
        else:
            import pkg_resources
            try:
                return pkg_resources.get_distribution(package_name).version
            except pkg_resources.DistributionNotFound:
                return None
    except Exception:
        return None


def compare_versions(version1: str, version2: str, operator: str) -> bool:
    """
    比较两个版本号
    """
    try:
        from packaging import version as pkg_version
        
        v1 = pkg_version.parse(version1)
        v2 = pkg_version.parse(version2)
        
        if operator == '==':
            return v1 == v2
        elif operator == '>=':
            return v1 >= v2
        elif operator == '<=':
            return v1 <= v2
        elif operator == '>':
            return v1 > v2
        elif operator == '<':
            return v1 < v2
        elif operator == '~=':
            return v1 >= v2 and v1.release[:2] == v2.release[:2]
        elif operator == '!=':
            return v1 != v2
        else:
            return True
    except Exception:
        return True


def check_dependencies(requirements_path: str = None) -> DependencyCheckResult:
    """
    检查所有依赖库版本是否匹配
    
    Args:
        requirements_path: requirements.txt 文件路径，默认为 main.py 同目录下的 requirements.txt
    
    Returns:
        DependencyCheckResult: 检查结果
    """
    try:
        if requirements_path is None:
            project_root = get_app_root()
            if is_macos() and os.path.exists(os.path.join(project_root, 'requirements-macos.txt')):
                requirements_path = os.path.join(project_root, 'requirements-macos.txt')
            else:
                requirements_path = os.path.join(project_root, 'requirements.txt')
        
        if not os.path.exists(requirements_path):
            return DependencyCheckResult(
                success=True,
                mismatches=[],
                missing_packages=[],
                error_message=None
            )
        
        required_packages = parse_requirements_file(requirements_path)
        mismatches = []
        missing_packages = []
        
        for package_name, (operator, required_version) in required_packages.items():
            installed_version = get_installed_version(package_name)
            
            if installed_version is None:
                missing_packages.append(package_name)
            elif operator and required_version:
                if not compare_versions(installed_version, required_version, operator):
                    mismatches.append(DependencyMismatch(
                        package_name=package_name,
                        required_version=f"{operator}{required_version}",
                        installed_version=installed_version,
                        operator=operator
                    ))
        
        success = len(mismatches) == 0 and len(missing_packages) == 0
        
        return DependencyCheckResult(
            success=success,
            mismatches=mismatches,
            missing_packages=missing_packages,
            error_message=None
        )
        
    except Exception as e:
        return DependencyCheckResult(
            success=True,
            mismatches=[],
            missing_packages=[],
            error_message=f"依赖检查过程中发生错误: {str(e)}"
        )


def format_dependency_error(result: DependencyCheckResult) -> str:
    """
    格式化依赖错误信息
    """
    lines = []
    lines.append("=" * 60)
    lines.append("依赖库版本检查失败")
    lines.append("=" * 60)
    lines.append("")
    
    if result.mismatches:
        lines.append("以下依赖库版本不兼容:")
        lines.append("-" * 60)
        for mismatch in result.mismatches:
            lines.append(f"  {mismatch.package_name}:")
            lines.append(f"    当前安装版本: {mismatch.installed_version}")
            lines.append(f"    所需版本: {mismatch.required_version}")
        lines.append("")
    
    if result.missing_packages:
        lines.append("以下依赖库未安装:")
        lines.append("-" * 60)
        for package in result.missing_packages:
            lines.append(f"  - {package}")
        lines.append("")
    
    lines.append("解决方案:")
    lines.append("-" * 60)
    lines.append("  请运行以下命令更新依赖库:")
    if is_macos():
        lines.append("  scripts/setup_macos.sh")
    else:
        lines.append("  pip install -r requirements.txt --upgrade")
    lines.append("")
    lines.append("  或者使用项目提供的安装脚本:")
    lines.append("  scripts/setup_macos.sh" if is_macos() else "  install_env.bat")
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


class DependencyErrorDialog:
    """依赖错误对话框 —— 基于 BaseDialog 的统一视觉风格。"""

    _CHUNK_SIZE = 15

    def __init__(self, result: DependencyCheckResult):
        self._result = result
        self._dialog = None
        self._on_install = None
        self._on_exit = None

    def exec_(self) -> bool:
        """显示对话框并返回用户选择（True=安装, False=退出）。"""
        try:
            from PyQt5.QtWidgets import QApplication, QLabel, QTextEdit, QFrame
            from PyQt5.QtCore import Qt
            from src.ui.widgets.base_dialog import BaseDialog
            from src.ui.design_tokens import get_tokens, get_token, scrollbar_qss

            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            t = get_tokens()
            error_message = format_dependency_error(self._result)

            # 摘要信息
            summary_parts = []
            if self._result.missing_packages:
                summary_parts.append(
                    f"{len(self._result.missing_packages)} 个包未安装"
                )
            if self._result.mismatches:
                summary_parts.append(
                    f"{len(self._result.mismatches)} 个包版本不兼容"
                )
            summary = "，".join(summary_parts)

            dialog = BaseDialog(
                parent=None,
                title="依赖库版本检查失败",
                width=520,
                height=420
            )
            dialog.set_title_icon("⚠️")

            # 内容区
            content_widget = dialog.content_widget
            content_layout = dialog.content_layout

            # 警告描述
            desc_label = QLabel(
                f"应用程序无法正常启动。\n检测到：{summary}"
            )
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(
                f"color: {t['text_primary']}; font-size: 13px; "
                "background: transparent; padding: 4px 0;"
            )
            content_layout.addWidget(desc_label)

            # 分隔线
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setFixedHeight(1)
            sep.setStyleSheet(
                f"background-color: {t['divider']}; border: none;"
            )
            content_layout.addWidget(sep)

            # 详细信息（可滚动）
            detail_label = QLabel("详细检查结果：")
            detail_label.setStyleSheet(
                f"color: {t['text_secondary']}; font-size: 12px; "
                "background: transparent; font-weight: bold;"
            )
            content_layout.addWidget(detail_label)

            detail_text = QTextEdit()
            detail_text.setReadOnly(True)
            detail_text.setPlainText(error_message)
            detail_text.setMinimumHeight(140)
            detail_text.setStyleSheet(
                f"background-color: {t['input_bg']}; "
                f"border: 1px solid {t['border_default']}; "
                f"border-radius: 8px; "
                f"color: {t['text_primary']}; "
                f"font-size: 12px; padding: 8px; "
                f"font-family: 'Consolas', 'Microsoft YaHei', monospace;"
                + scrollbar_qss()
            )
            content_layout.addWidget(detail_text)

            # 操作提示
            hint_label = QLabel(
                "选择「自动修复」将运行安装脚本，或选择「退出」稍后手动修复。"
            )
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet(
                f"color: {t['text_disabled']}; font-size: 12px; "
                "background: transparent;"
            )
            content_layout.addWidget(hint_label)

            # 按钮
            dialog.add_secondary_button("退出程序", self._handle_exit)
            dialog.add_primary_button("自动修复", self._handle_install)

            dialog.show()
            self._dialog = dialog

            # 阻塞事件循环等待用户选择
            self._user_choice = None
            while self._user_choice is None:
                app.processEvents()

            return self._user_choice

        except Exception as e:
            print(format_dependency_error(self._result))
            print(f"\n无法显示图形界面错误对话框: {e}")
            return False

    def _handle_install(self):
        self._user_choice = True
        if self._dialog:
            self._dialog.close()

    def _handle_exit(self):
        self._user_choice = False
        if self._dialog:
            self._dialog.close()


def show_dependency_error_dialog(result: DependencyCheckResult):
    """
    显示依赖错误的图形界面对话框，并提供自动安装选项。
    使用统一的 BaseDialog 视觉风格。
    """
    dialog = DependencyErrorDialog(result)

    if dialog.exec_():
        # 用户选择安装
        project_root = get_app_root()
        install_script = os.path.join(
            project_root, "scripts", "setup_macos.sh"
        ) if is_macos() else os.path.join(project_root, "install_env.bat")

        if os.path.exists(install_script):
            if is_windows():
                subprocess.Popen(['cmd', '/c', install_script], cwd=project_root)
            else:
                subprocess.Popen([install_script], cwd=project_root)
            sys.exit(0)
        else:
            # 如果安装脚本不存在，也用统一弹窗提示
            try:
                from src.ui.widgets.base_dialog import BaseDialog
                from PyQt5.QtWidgets import QLabel, QApplication
                from src.ui.design_tokens import get_token

                fallback = BaseDialog(
                    parent=None, title="错误", width=400, height=180
                )
                fallback.set_title_icon("❌")
                msg = QLabel(
                    f"找不到安装脚本：{install_script}\n请手动运行 install_env.bat"
                )
                msg.setWordWrap(True)
                msg.setStyleSheet(
                    f"color: {get_token('text_primary')}; font-size: 13px; "
                    "background: transparent;"
                )
                fallback.content_layout.addWidget(msg)
                fallback.add_cancel_button("退出")
                fallback.show()
                app = QApplication.instance()
                if app:
                    # 简单阻塞
                    fallback.rejected.connect(lambda: sys.exit(1))
            except Exception:
                pass
            sys.exit(1)
    else:
        sys.exit(1)


def check_and_exit_on_failure(requirements_path: str = None) -> bool:
    """
    检查依赖版本，如果失败则显示错误并退出程序
    
    Args:
        requirements_path: requirements.txt 文件路径
    
    Returns:
        bool: 检查是否通过
    """
    result = check_dependencies(requirements_path)
    
    if not result.success:
        show_dependency_error_dialog(result)
        sys.exit(1)
        return False
    
    if result.error_message:
        print(f"警告: {result.error_message}")
    
    return True
