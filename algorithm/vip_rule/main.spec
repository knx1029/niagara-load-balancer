# -*- mode: python -*-
a = Analysis(['main.py', 'single_vip.py', 'multiple_vip.py', 'hw_layers.py', 'group.py', 'vip_curve.py', 'vip_rule.py', 'suffix_forest.py'],
             pathex=['/Users/nanxikang/Documents/Research/github/Niagara/simulation/vip_rule'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='main',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='main')
