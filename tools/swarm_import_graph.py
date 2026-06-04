import ast, os, csv
from collections import defaultdict

root_pkg = 'quant_ecosystem/cognition/swarm'
repo_root = '.'

# map file path -> module name
file_to_module = {}
for dirpath, dirnames, filenames in os.walk('quant_ecosystem'):
    for fname in filenames:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(dirpath, fname)
        rel = os.path.relpath(fpath).replace('\\','/')
        # compute module name like quant_ecosystem.path.file
        parts = rel.split('/')
        if parts[-1] == '__init__.py':
            mod = '.'.join(parts[:-1]).replace('/','.')
        else:
            mod = '.'.join(parts).rsplit('.py',1)[0].replace('/','.')
        file_to_module[rel] = mod

# list of swarm modules
swarm_files = [p for p in file_to_module.keys() if p.startswith(root_pkg) and p.endswith('.py')]
swarm_modules = {file_to_module[p]: p for p in swarm_files}

# prepare maps
imports_by = defaultdict(set)   # module -> set of files that import it
imports_of = defaultdict(set)   # module -> set of modules it imports

# parse all python files for imports
for fpath, modname in file_to_module.items():
    try:
        src = open(fpath, 'r', encoding='utf-8').read()
    except Exception:
        continue
    try:
        tree = ast.parse(src)
    except Exception:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                name = n.name
                # if imports a swarm module
                for smod, sfile in swarm_modules.items():
                    if name == smod or name.startswith(smod + '.'):
                        imports_by[smod].add(fpath)
                        imports_of[modname].add(smod)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            level = node.level
            # resolve relative imports
            if level and (fpath.startswith(root_pkg)):
                # compute importing module's package
                importing_mod = file_to_module[fpath]
                pkg_parts = importing_mod.split('.')
                if level <= len(pkg_parts):
                    base = '.'.join(pkg_parts[:-level+1]) if level>1 else '.'.join(pkg_parts[:-1])
                else:
                    base = '.'.join(pkg_parts[:-1])
                if mod:
                    target = base + '.' + mod if base else mod
                else:
                    target = base
            else:
                target = mod
            if target:
                for smod in swarm_modules.keys():
                    if target == smod or target.startswith(smod + '.'):
                        imports_by[smod].add(fpath)
                        imports_of[modname].add(smod)

# test coverage: check tests directory for references to module
test_refs = defaultdict(set)
for dirpath, dirnames, filenames in os.walk('.'):
    if 'tests' not in dirpath and not dirpath.startswith('./tests'):
        # still scan all, tests may be in tests/ or elsewhere
        pass
for dirpath, dirnames, filenames in os.walk('.'):
    for fname in filenames:
        if not fname.endswith('.py'):
            continue
        if '/tests/' in os.path.join(dirpath, fname).replace('\\','/') or dirpath.endswith('tests') or dirpath.startswith('tests'):
            fpath = os.path.join(dirpath, fname)
            try:
                txt = open(fpath, 'r', encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            for smod, sfile in swarm_modules.items():
                if smod in txt or os.path.basename(sfile).replace('.py','') in txt:
                    test_refs[smod].add(fpath)

# produce report
os.makedirs('FORENSIC_AUDIT_OUTPUT', exist_ok=True)
with open('FORENSIC_AUDIT_OUTPUT/SWARM_IMPORT_GRAPH.csv','w',newline='',encoding='utf-8') as csvf:
    writer = csv.writer(csvf)
    writer.writerow(['Module','File','ImportedByCount','ImportedByFiles','ImportsCount','ImportsModules','TestRefsCount','TestFiles','ConnectionScore'])
    for smod, sfile in sorted(swarm_modules.items()):
        imported_by = sorted(list(imports_by.get(smod, [])))
        imports = sorted(list(imports_of.get(sfile_to_module := file_to_module.get(sfile, ''), []))) if file_to_module.get(sfile, None) else []
        tests = sorted(list(test_refs.get(smod, [])))
        # compute connection score
        outside_importers = [p for p in imported_by if not p.startswith(root_pkg)]
        ib_count = len(imported_by)
        if ib_count >= 6 or (ib_count>0 and any(p for p in outside_importers)):
            score = 'Core'
        elif ib_count >= 2:
            score = 'Active'
        elif ib_count == 1:
            score = 'Partial'
        elif ib_count == 0 and imports:
            score = 'Isolated'
        else:
            score = 'Dead'
        writer.writerow([smod, sfile, ib_count, '\n'.join(imported_by), len(imports), '\n'.join(imports), len(tests), '\n'.join(tests), score])

# also write markdown connectivity matrix
with open('FORENSIC_AUDIT_OUTPUT/SWARM_CONNECTIVITY.md','w',encoding='utf-8') as md:
    md.write('| Module | File | Imported By (count) | Imports | Tests (count) | Connection Score |\n')
    md.write('|---|---|---:|---|---:|---|\n')
    for smod, sfile in sorted(swarm_modules.items()):
        imported_by = sorted(list(imports_by.get(smod, [])))
        imports = sorted(list(imports_of.get(file_to_module.get(sfile,''), [])))
        tests = sorted(list(test_refs.get(smod, [])))
        ib_count = len(imported_by)
        if ib_count >= 6 or (ib_count>0 and any(p for p in imported_by if not p.startswith(root_pkg))):
            score = 'Core'
        elif ib_count >= 2:
            score = 'Active'
        elif ib_count == 1:
            score = 'Partial'
        elif ib_count == 0 and imports:
            score = 'Isolated'
        else:
            score = 'Dead'
        md.write(f'| {smod} | {sfile} | {ib_count} | {", ".join([os.path.basename(x) for x in imports])} | {len(tests)} | {score} |\n')

print('WROTE FORENSIC_AUDIT_OUTPUT/SWARM_IMPORT_GRAPH.csv and SWARM_CONNECTIVITY.md')
