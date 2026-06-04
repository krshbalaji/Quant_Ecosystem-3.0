import ast, os, re
from collections import defaultdict

root = 'quant_ecosystem/cognition/swarm'
entries = []

name_graph_keywords = ['edge','edges','graph','adj','neighbor','neighbors','adjacency']
event_keywords = ['subscribe','subscription','subscriptions','subscribers','handler','handlers','listeners']
workflow_keywords = ['workflow','stage','stages','step','steps','pipeline','orchestration']

for dirpath, dirnames, filenames in os.walk(root):
    for fname in filenames:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(dirpath, fname)
        rel = os.path.relpath(fpath).replace('\\','/')
        try:
            src = open(fpath, 'r', encoding='utf-8').read()
        except Exception:
            continue
        try:
            tree = ast.parse(src)
        except Exception:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                collections = set()
                details = []
                # class-level assigns
                for c in node.body:
                    if isinstance(c, ast.Assign):
                        val = c.value
                        targ_names = []
                        for t in c.targets:
                            if isinstance(t, ast.Name):
                                targ_names.append(t.id)
                            elif isinstance(t, ast.Attribute):
                                targ_names.append(t.attr)
                        if isinstance(val, ast.List):
                            collections.add('List')
                            details.append(('class_attr', ','.join(targ_names), 'List'))
                        elif isinstance(val, ast.Set):
                            collections.add('Set')
                            details.append(('class_attr', ','.join(targ_names), 'Set'))
                        elif isinstance(val, ast.Dict):
                            collections.add('Dict')
                            details.append(('class_attr', ','.join(targ_names), 'Dict'))
                        elif isinstance(val, ast.Call):
                            if isinstance(val.func, ast.Name) and val.func.id in ('dict','defaultdict'):
                                collections.add('Dict')
                                details.append(('class_attr', ','.join(targ_names), 'Dict'))
                # inspect methods for self.* assignments and annotations
                for c in node.body:
                    if isinstance(c, ast.FunctionDef):
                        for stmt in ast.walk(c):
                            if isinstance(stmt, ast.Assign):
                                for t in stmt.targets:
                                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == 'self':
                                        name = t.attr
                                        v = stmt.value
                                        if isinstance(v, ast.List):
                                            collections.add('List')
                                            details.append(('init_attr', name, 'List'))
                                        elif isinstance(v, ast.Dict):
                                            collections.add('Dict')
                                            details.append(('init_attr', name, 'Dict'))
                                        elif isinstance(v, ast.Set):
                                            collections.add('Set')
                                            details.append(('init_attr', name, 'Set'))
                                        elif isinstance(v, ast.Call):
                                            fn = ''
                                            if isinstance(v.func, ast.Name):
                                                fn = v.func.id
                                            elif isinstance(v.func, ast.Attribute):
                                                fn = v.func.attr
                                            if fn in ('list','set'):
                                                collections.add(fn.capitalize())
                                                details.append(('init_attr', name, fn.capitalize()))
                                            if fn in ('dict','defaultdict'):
                                                collections.add('Dict')
                                                details.append(('init_attr', name, 'Dict'))
                            if isinstance(stmt, ast.AnnAssign):
                                # self.x: List[...] = [] or class attr annotations
                                target = stmt.target
                                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                                    ann = stmt.annotation
                                    ann_s = ast.unparse(ann) if hasattr(ast, 'unparse') else ''
                                    if 'List' in ann_s or 'list' in ann_s:
                                        collections.add('List')
                                        details.append(('ann_attr', target.attr, 'List'))
                                    if 'Dict' in ann_s or 'dict' in ann_s:
                                        collections.add('Dict')
                                        details.append(('ann_attr', target.attr, 'Dict'))
                if collections:
                    # Purpose classification heuristic
                    purpose = 'Domain Aggregate'
                    names = ' '.join([d[1] for d in details])
                    lname = names.lower()
                    if any(k in lname for k in event_keywords):
                        purpose = 'EventBus candidate'
                    elif any(k in lname for k in workflow_keywords):
                        purpose = 'WorkflowStore candidate'
                    elif any(k in lname for k in name_graph_keywords):
                        purpose = 'GraphStore candidate'
                    else:
                        # check if dict of lists pattern via annotations or code
                        if any(d[2]=='Dict' for d in details) and any(d[2]=='List' for d in details):
                            purpose = 'MultiMap candidate'
                        elif any(d[2]=='List' for d in details) and len(details)==1:
                            purpose = 'AppendRegistry candidate'
                        elif any(d[2]=='Dict' for d in details) and len(details)==1:
                            purpose = 'KeyedRegistry candidate'
                        else:
                            purpose = 'Infrastructure Component'
                    entries.append((rel, class_name, '|'.join(sorted(collections)), purpose, details))

# write markdown
out = ['| File path | Class name | Collection type | Purpose classification |','|---|---:|---|---|']
for e in entries:
    rel, cn, ctype, purpose, details = e
    out.append(f'| {rel} | {cn} | {ctype} | {purpose} |')

os.makedirs('FORENSIC_AUDIT_OUTPUT', exist_ok=True)
with open('FORENSIC_AUDIT_OUTPUT/SWARM_COLLECTION_AUDIT.md','w',encoding='utf-8') as f:
    f.write('\n'.join(out))
print('WROTE FORENSIC_AUDIT_OUTPUT/SWARM_COLLECTION_AUDIT.md')
