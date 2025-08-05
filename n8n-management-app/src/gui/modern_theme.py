"""
Modern UI Theme System for n8n Management App
Provides beautiful, accessible, and user-friendly styling
"""

import tkinter as tk
from tkinter import ttk
import platform


class ModernTheme:
    """Modern theme with beautiful colors and typography"""
    
    # Color Palette - Inspired by modern design systems
    COLORS = {
        # Primary colors
        'primary': '#2563eb',      # Blue 600
        'primary_hover': '#1d4ed8', # Blue 700
        'primary_light': '#dbeafe', # Blue 100
        'primary_dark': '#1e40af',  # Blue 800
        
        # Secondary colors
        'secondary': '#64748b',     # Slate 500
        'secondary_light': '#f1f5f9', # Slate 100
        'secondary_dark': '#334155', # Slate 700
        
        # Status colors
        'success': '#10b981',       # Emerald 500
        'success_light': '#d1fae5', # Emerald 100
        'warning': '#f59e0b',       # Amber 500
        'warning_light': '#fef3c7', # Amber 100
        'error': '#ef4444',         # Red 500
        'error_light': '#fee2e2',   # Red 100
        'info': '#3b82f6',          # Blue 500
        'info_light': '#dbeafe',    # Blue 100
        
        # Neutral colors
        'white': '#ffffff',
        'gray_50': '#f9fafb',
        'gray_100': '#f3f4f6',
        'gray_200': '#e5e7eb',
        'gray_300': '#d1d5db',
        'gray_400': '#9ca3af',
        'gray_500': '#6b7280',
        'gray_600': '#4b5563',
        'gray_700': '#374151',
        'gray_800': '#1f2937',
        'gray_900': '#111827',
        
        # Background colors
        'bg_primary': '#ffffff',
        'bg_secondary': '#f8fafc',
        'bg_tertiary': '#f1f5f9',
        'bg_dark': '#0f172a',
        
        # Text colors
        'text_primary': '#1f2937',
        'text_secondary': '#6b7280',
        'text_muted': '#9ca3af',
        'text_inverse': '#ffffff',
        
        # Border colors
        'border_light': '#e5e7eb',
        'border_medium': '#d1d5db',
        'border_dark': '#9ca3af',
    }
    
    # Typography
    FONTS = {
        'heading_large': ('Segoe UI', 24, 'bold'),
        'heading_medium': ('Segoe UI', 18, 'bold'),
        'heading_small': ('Segoe UI', 14, 'bold'),
        'body_large': ('Segoe UI', 12, 'normal'),
        'body_medium': ('Segoe UI', 11, 'normal'),
        'body_small': ('Segoe UI', 10, 'normal'),
        'caption': ('Segoe UI', 9, 'normal'),
        'code': ('Consolas', 10, 'normal'),
        'button': ('Segoe UI', 10, 'normal'),
    }
    
    # Spacing
    SPACING = {
        'xs': 4,
        'sm': 8,
        'md': 16,
        'lg': 24,
        'xl': 32,
        'xxl': 48,
    }
    
    # Border radius
    RADIUS = {
        'sm': 4,
        'md': 6,
        'lg': 8,
        'xl': 12,
        'full': 9999,
    }
    
    def __init__(self, root):
        self.root = root
        self.style = ttk.Style()
        self._setup_theme()
    
    def _setup_theme(self):
        """Setup the modern theme"""
        # Use the best available theme as base
        available_themes = self.style.theme_names()
        
        if platform.system() == 'Windows':
            if 'winnative' in available_themes:
                self.style.theme_use('winnative')
            elif 'vista' in available_themes:
                self.style.theme_use('vista')
        elif platform.system() == 'Darwin':
            if 'aqua' in available_themes:
                self.style.theme_use('aqua')
        else:
            if 'clam' in available_themes:
                self.style.theme_use('clam')
            elif 'alt' in available_themes:
                self.style.theme_use('alt')
        
        # Configure custom styles
        self._configure_styles()
    
    def _configure_styles(self):
        """Configure all custom styles"""
        
        # Configure root window
        self.root.configure(bg=self.COLORS['bg_primary'])       
        # Button styles
        self.style.configure('Primary.TButton',
            background=self.COLORS['primary'],
            foreground=self.COLORS['text_inverse'],
            font=self.FONTS['button'],
            borderwidth=0,
            focuscolor='none',
            padding=(16, 8))
        
        self.style.map('Primary.TButton',
            background=[('active', self.COLORS['primary_hover']),
                       ('pressed', self.COLORS['primary_dark'])])
        
        self.style.configure('Secondary.TButton',
            background=self.COLORS['gray_100'],
            foreground=self.COLORS['text_primary'],
            font=self.FONTS['button'],
            borderwidth=1,
            relief='solid',
            focuscolor='none',
            padding=(16, 8))
        
        self.style.map('Secondary.TButton',
            background=[('active', self.COLORS['gray_200']),
                       ('pressed', self.COLORS['gray_300'])])
        
        self.style.configure('Success.TButton',
            background=self.COLORS['success'],
            foreground=self.COLORS['text_inverse'],
            font=self.FONTS['button'],
            borderwidth=0,
            focuscolor='none',
            padding=(12, 6))
        
        self.style.configure('Warning.TButton',
            background=self.COLORS['warning'],
            foreground=self.COLORS['text_inverse'],
            font=self.FONTS['button'],
            borderwidth=0,
            focuscolor='none',
            padding=(12, 6))
        
        self.style.configure('Error.TButton',
            background=self.COLORS['error'],
            foreground=self.COLORS['text_inverse'],
            font=self.FONTS['button'],
            borderwidth=0,
            focuscolor='none',
            padding=(12, 6))
        
        # Label styles
        self.style.configure('Heading.Large.TLabel',
            font=self.FONTS['heading_large'],
            foreground=self.COLORS['text_primary'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Heading.Medium.TLabel',
            font=self.FONTS['heading_medium'],
            foreground=self.COLORS['text_primary'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Heading.Small.TLabel',
            font=self.FONTS['heading_small'],
            foreground=self.COLORS['text_primary'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Body.Large.TLabel',
            font=self.FONTS['body_large'],
            foreground=self.COLORS['text_primary'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Body.Medium.TLabel',
            font=self.FONTS['body_medium'],
            foreground=self.COLORS['text_secondary'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Caption.TLabel',
            font=self.FONTS['caption'],
            foreground=self.COLORS['text_muted'],
            background=self.COLORS['bg_primary'])
        
        # Status labels
        self.style.configure('Success.TLabel',
            font=self.FONTS['body_medium'],
            foreground=self.COLORS['success'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Warning.TLabel',
            font=self.FONTS['body_medium'],
            foreground=self.COLORS['warning'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Error.TLabel',
            font=self.FONTS['body_medium'],
            foreground=self.COLORS['error'],
            background=self.COLORS['bg_primary'])
        
        self.style.configure('Info.TLabel',
            font=self.FONTS['body_medium'],
            foreground=self.COLORS['info'],
            background=self.COLORS['bg_primary'])
        
        # Frame styles
        self.style.configure('Card.TFrame',
            background=self.COLORS['white'],
            relief='solid',
            borderwidth=1,
            bordercolor=self.COLORS['border_light'])
        
        self.style.configure('Sidebar.TFrame',
            background=self.COLORS['bg_secondary'],
            relief='flat',
            borderwidth=0)
        
        self.style.configure('Toolbar.TFrame',
            background=self.COLORS['white'],
            relief='solid',
            borderwidth=0)
        
        # Notebook styles
        self.style.configure('Modern.TNotebook',
            background=self.COLORS['bg_primary'],
            borderwidth=0,
            tabmargins=[0, 0, 0, 0])
        
        self.style.configure('Modern.TNotebook.Tab',
            background=self.COLORS['gray_100'],
            foreground=self.COLORS['text_secondary'],
            font=self.FONTS['body_medium'],
            padding=[16, 12],
            borderwidth=0)
        
        self.style.map('Modern.TNotebook.Tab',
            background=[('selected', self.COLORS['white']),
                       ('active', self.COLORS['gray_200'])],
            foreground=[('selected', self.COLORS['text_primary']),
                       ('active', self.COLORS['text_primary'])])
        
        # Entry styles
        self.style.configure('Modern.TEntry',
            font=self.FONTS['body_medium'],
            borderwidth=1,
            relief='solid',
            bordercolor=self.COLORS['border_medium'],
            padding=(12, 8))
        
        self.style.map('Modern.TEntry',
            bordercolor=[('focus', self.COLORS['primary'])])
        
        # Treeview styles
        self.style.configure('Modern.Treeview',
            font=self.FONTS['body_medium'],
            background=self.COLORS['white'],
            foreground=self.COLORS['text_primary'],
            borderwidth=1,
            relief='solid',
            bordercolor=self.COLORS['border_light'],
            rowheight=32)
        
        self.style.configure('Modern.Treeview.Heading',
            font=self.FONTS['heading_small'],
            background=self.COLORS['gray_50'],
            foreground=self.COLORS['text_primary'],
            borderwidth=1,
            relief='solid',
            bordercolor=self.COLORS['border_light'])
        
        self.style.map('Modern.Treeview',
            background=[('selected', self.COLORS['primary_light'])],
            foreground=[('selected', self.COLORS['text_primary'])])
        
        # Progressbar styles
        self.style.configure('Modern.Horizontal.TProgressbar',
            background=self.COLORS['primary'],
            troughcolor=self.COLORS['gray_200'],
            borderwidth=0,
            lightcolor=self.COLORS['primary'],
            darkcolor=self.COLORS['primary'])
        
        # Separator styles
        self.style.configure('Modern.TSeparator',
            background=self.COLORS['border_light'])
    
    def create_status_indicator(self, parent, status='unknown'):
        """Create a modern status indicator"""
        status_colors = {
            'running': self.COLORS['success'],
            'stopped': self.COLORS['error'],
            'starting': self.COLORS['warning'],
            'healthy': self.COLORS['success'],
            'unhealthy': self.COLORS['error'],
            'unknown': self.COLORS['gray_400']
        }
        
        color = status_colors.get(status, self.COLORS['gray_400'])
        
        # Create a colored circle indicator
        canvas = tk.Canvas(parent, width=12, height=12, 
                          bg=self.COLORS['bg_primary'], 
                          highlightthickness=0)
        canvas.create_oval(2, 2, 10, 10, fill=color, outline=color)
        return canvas
    
    def create_card_frame(self, parent, **kwargs):
        """Create a modern card-style frame"""
        frame = ttk.Frame(parent, style='Card.TFrame', **kwargs)
        return frame
    
    def create_icon_button(self, parent, text, command=None, style='Primary.TButton'):
        """Create a modern icon button"""
        button = ttk.Button(parent, text=text, command=command, style=style)
        return button


def apply_modern_theme(root):
    """Apply modern theme to the application"""
    return ModernTheme(root)