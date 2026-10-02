# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package config_audit): 4 comments

`scratchpad/cycle10/p5_V_1/config_audit`

### 1. inputs.py:58

```python
     50     deprecated_keys = _parseDeprecatedKeys(_readTomlFile(deprecated_path), deprecated_path)
     51 
     52     layer_names = sorted({name for environment in environments for name in environment.layers})
     53     layer_tables = {name: _readTomlFile(input_dir / f'{name}.toml') for name in layer_names}
     54     return AuditInputs(current_version, secret_key_pattern, environments, deprecated_keys, layer_tables)
     55 
     56 
     57 def _rejectInput(input_path: Path, reason: str) -> UnusableInputError:
>>   58     # stacklevel=2 puts the raise site's function and line in the record
     59     _LOG.error('input.rejected', extra={'path': str(input_path), 'reason': reason}, stacklevel=2)
     60     return UnusableInputError(f'{input_path}: {reason}')
     61 
     62 
     63 def _readTomlFile(toml_path: Path) -> TomlTable:
     64     """Parse one TOML file.
     65 
     66     Raises:
     67         UnusableInputError: the file is missing, unreadable, not UTF-8 or not valid TOML.
     68     """
```

### 2. merge.py:70

```python
     62                 stale_origins = [
     63                     origin for origin in self.origins if origin.segments[: len(path.segments)] == path.segments
     64                 ]
     65                 for origin in stale_origins:
     66                     del self.origins[origin]
     67 
     68             self.origins[path] = layer_name
     69             if isinstance(value, dict):
>>   70                 # inserting the layer's own table would make a later merge write into a parsed document
>>   71                 # shared by every environment with this layer
     72                 table: TomlTable = {}
     73                 target[key] = table
     74                 self.mergeTable(table, value, path, layer_name)
     75             else:
     76                 target[key] = value
```

### 3. rules.py:122

```python
    114             layer = max(share_layers, key=merged.environment.layers.index, default=merged.origins[arms_path])
    115             detail = f'shares sum to {sum(shares)}; must sum to 100'
    116             findings.append(Finding(FindingKind.BAD_ROLLOUT, arms_path, layer, detail))
    117 
    118     return findings
    119 
    120 
    121 def _readPercentage(value: TomlValue | None) -> int | None:
>>  122     # without the bool test, TOML true passes as 1
    123     if isinstance(value, bool) or not isinstance(value, int):
    124         return None
    125     return value if 0 <= value <= 100 else None
    126 
    127 
    128 def _describeSetting(value: TomlValue | None) -> str:
    129     if value is None:
    130         return 'missing'
    131     value_type = classifyTomlValue(value).value
    132     match value:
```

### 4. toml_type.py:18

```python
     10 from __future__ import annotations
     11 
     12 from datetime import date, datetime, time
     13 
     14 from config_audit.vocabulary import TomlType, TomlValue
     15 
     16 
     17 def classifyTomlValue(value: TomlValue) -> TomlType:
>>   18     # bool subclasses int and datetime subclasses date, so each subclass must match first
     19     match value:
     20         case bool():
     21             return TomlType.BOOLEAN
     22         case int():
     23             return TomlType.INTEGER
     24         case float():
     25             return TomlType.FLOAT
     26         case str():
     27             return TomlType.STRING
     28         case datetime():
```

## Run 2 (package layer_audit): 4 comments

`scratchpad/cycle10/p5_V_2/layer_audit`

### 5. merge.py:36

```python
     28 ) -> tuple[MergedConfig, list[Finding]]:
     29     merge = _LayerMerge()
     30     for layer in layers:
     31         merge.mergeTable(merge.tree, layer_tables[layer], prefix=(), layer=layer)
     32     return MergedConfig(merge.tree, merge.indexKeys((), merge.tree)), merge.type_changes
     33 
     34 
     35 def classifyTomlValue(value: object) -> TomlType:
>>   36     # bool subclasses int and datetime subclasses date, so each subclass is tested first
     37     if isinstance(value, bool):
     38         return TomlType.BOOLEAN
     39     if isinstance(value, int):
     40         return TomlType.INTEGER
     41     if isinstance(value, float):
     42         return TomlType.FLOAT
     43     if isinstance(value, str):
     44         return TomlType.STRING
     45     if isinstance(value, datetime):
     46         return TomlType.DATETIME
```

### 6. merge.py:59

```python
     51     if isinstance(value, list):
     52         return TomlType.ARRAY
     53     if isinstance(value, dict):
     54         return TomlType.TABLE
     55     raise TypeError(f'tomllib returns no {type(value).__name__}')
     56 
     57 
     58 def joinKeyPath(key_path: KeyPath) -> str:
>>   59     # dotted form, as in deprecated.toml and in the audit's findings
     60     return '.'.join(key_path)
     61 
     62 
     63 ### vocabulary #########################################################################
     64 
     65 
     66 class _LayerMerge:
     67     def __init__(self) -> None:
     68         self.tree: dict[str, object] = {}
     69         self.set_by: dict[KeyPath, LayerName] = {}
```

### 7. merge.py:95

```python
     87                     continue
     88 
     89                 earlier_type, layer_type = classifyTomlValue(earlier), classifyTomlValue(value)
     90                 if earlier_type != layer_type:
     91                     detail = f'{earlier_type.value} in {self.set_by[key_path]}, {layer_type.value} in {layer}'
     92                     self.type_changes.append(Finding(FindingKind.TYPE_CHANGE, joinKeyPath(key_path), layer, detail))
     93                 self.forgetKeysBelow(key_path)
     94 
>>   95             # without the copy, merging a later layer alters this layer's parsed table for the next environment
     96             merged_table[key] = copy.deepcopy(value)
     97             self.recordSetBy(key_path, value, layer)
     98 
     99     def forgetKeysBelow(self, key_path: KeyPath) -> None:
    100         depth = len(key_path)
    101         below = [known for known in self.set_by if len(known) > depth and known[:depth] == key_path]
    102         for known in below:
    103             del self.set_by[known]
    104 
    105     def recordSetBy(self, key_path: KeyPath, value: object, layer: LayerName) -> None:
```

### 8. rules.py:96

```python
     88     return [(*table_path, key) for key in entry.value]
     89 
     90 
     91 def _parsePercentage(config: MergedConfig, key_path: KeyPath, owner_path: KeyPath) -> int | Finding:
     92     expected = f'expected an integer from {PERCENT_MIN} to {PERCENT_MAX}'
     93     entry = config.keys.get(key_path)
     94     if entry is None:
     95         return _buildRolloutFinding(key_path, config.keys[owner_path].layer, f'missing, {expected}')
>>   96     # without the bool test, true passes as the integer 1
     97     if isinstance(entry.value, int) and not isinstance(entry.value, bool) and PERCENT_MIN <= entry.value <= PERCENT_MAX:
     98         return entry.value
     99     detail = f'got {classifyTomlValue(entry.value).value} {entry.value!r}, {expected}'
    100     return _buildRolloutFinding(key_path, entry.layer, detail)
    101 
    102 
    103 def _buildRolloutFinding(key_path: KeyPath, layer: LayerName, detail: str) -> Finding:
    104     return Finding(FindingKind.BAD_ROLLOUT, joinKeyPath(key_path), layer, detail)
```
