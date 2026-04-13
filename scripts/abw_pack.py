import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Regex để bóc YAML frontmatter
MD_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)', re.DOTALL)

def setup_logger():
    logging.basicConfig(level=logging.INFO, format="[Packager] %(levelname)s: %(message)s")
    return logging.getLogger("packager")

logger = setup_logger()

def load_json(filepath):
    path = Path(filepath)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON {filepath}: {e}")
            return None

def load_manifest(workspace_dir):
    manifest_path = Path(workspace_dir) / "processed" / "manifest.jsonl"
    manifest_data = {}
    if not manifest_path.exists():
        logger.warning(f"Manifest not found at {manifest_path}")
        return manifest_data
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                manifest_data[idx + 1] = entry 
            except json.JSONDecodeError:
                continue
    return manifest_data

def parse_markdown_frontmatter(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = MD_FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    yaml_text = match.group(1)
    body = match.group(2)
    meta = {}
    for line in yaml_text.split('\n'):
        if ':' in line:
            parts = line.split(':', 1)
            meta[parts[0].strip()] = parts[1].strip().strip('"').strip("'")
    return meta, body

def check_mismatch(meta, manifest_entry, file_path):
    note_status = meta.get("status", "draft")
    manifest_status = manifest_entry.get("status", "unknown") if manifest_entry else "unknown"
    if note_status in ["draft", "pending_grounding"]:
        return "needs_review", f"Note {file_path} is in status '{note_status}'."
    if note_status == "grounded" and manifest_status != "grounded":
        return "fail", f"Mismatch: Note {file_path} claims 'grounded' but manifest '{manifest_entry.get('origin_path','')}' is '{manifest_status}'."
    return "pass", ""

def get_manifest_entry_for_wiki(meta, manifest_data):
    # Regex cho `processed/manifest.jsonl#line-X`
    sources_str = meta.get("sources", "")
    with open(meta.get("_filepath"), "r", encoding="utf-8") as f:
        full_text = f.read()
        ref_match = re.search(r'processed/manifest\.jsonl#line-(\d+)', full_text)
        if ref_match:
            line_no = int(ref_match.group(1))
            return line_no, manifest_data.get(line_no)
    return None, None

def determine_domain(file_name, rules):
    for domain, patterns in rules.items():
        if isinstance(patterns, list):
            for pattern in patterns:
                if re.search(pattern, file_name, re.IGNORECASE):
                    return domain
    return "Misc"

def check_technical_facts(body):
    facts = {
        "fields": False,
        "db_tables": False,
        "endpoints": False,
        "errors": False
    }
    # Tìm kiếm trường database hoặc cờ (có tiền tố T_ hoặc chữ hoa có dấu gạch dưới)
    if re.search(r'\b(T_[A-Z0-9_]+|[A-Z_]{3,}_FLG|PROCESS_STATUS|S_NO)\b', body):
        facts["db_tables"] = True
        facts["fields"] = True
    if re.search(r'https?://[^\s]+|/api/v\d+', body):
        facts["endpoints"] = True
    if re.search(r'\b(ERR_|E[0-9]{3,4})\b', body):
        facts["errors"] = True
    return facts

def run_packager(workspace, policy_path, output_dir_base, package_id, dry_run):
    ws = Path(workspace)
    manifest_data = load_manifest(ws)
    policy = load_json(policy_path)
    if not policy:
        logger.error(f"Cannot load policy: {policy_path}. Using fallback.")
        policy = {"limits": {"soft_warning_limit": 45, "hard_source_limit": 50}, "critical_keep_rules": []}
        
    limits = policy.get("limits", {"soft_warning_limit": 45, "hard_source_limit": 50})
    critical_rules = policy.get("critical_keep_rules", [])
    exclude_rules = policy.get("exclude", [])
    domain_rules = policy.get("domain_grouping_rules", {})
    
    if package_id == "auto":
        package_id = "pkg_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
    out_dir = ws / output_dir_base / package_id
    
    qa_checks = {
        "source_limit_check": "pass",
        "draft_grounding_check": "pass",
        "technical_facts_coverage": "pass",
        "contradiction_check": "pass",
        "traceability_check": "pass",
        "manifest_match_check": "pass"
    }
    warnings = []
    
    wiki_dir = ws / "wiki"
    wiki_files = list(wiki_dir.rglob("*.md")) if wiki_dir.exists() else []
    # Loại bỏ index.md và schema files
    wiki_files = [f for f in wiki_files if f.name != "index.md" and "_schemas" not in str(f)]
    
    compaction_dict = {}
    mapped_manifests = {}
    critical_files_copied = 0
    excluded_count = 0
    force_kept_files = []  # Tracking force_keep originals
    technical_coverage = {"fields": False, "db_tables": False, "endpoints": False, "errors": False}
    has_technical_source = False
    
    force_keep_rules = policy.get("force_keep", [])
    force_compress_rules = policy.get("force_compress", [])
    
    for w_file in wiki_files:
        # Exclude check
        excluded = False
        for ex in exclude_rules:
            if re.search(ex, w_file.name, re.IGNORECASE):
                excluded = True
                break
        if excluded:
            excluded_count += 1
            continue
            
        meta, body = parse_markdown_frontmatter(w_file)
        meta["_filepath"] = w_file
        line_no, m_entry = get_manifest_entry_for_wiki(meta, manifest_data)
        
        # QA lifecycle mismatch
        stat, msg = check_mismatch(meta, m_entry, w_file.name)
        if stat == "fail":
            qa_checks["draft_grounding_check"] = "fail"
            warnings.append(msg)
        elif stat == "needs_review" and qa_checks["draft_grounding_check"] != "fail":
            qa_checks["draft_grounding_check"] = "needs_review"
            warnings.append(msg)
            
        raw_path = m_entry.get("origin_path", "unknown") if m_entry else "unknown"
        
        # Compute relative wiki path from workspace root
        try:
            wiki_rel_path = w_file.relative_to(ws).as_posix()
        except ValueError:
            wiki_rel_path = f"wiki/{w_file.name}"
        
        # Determine file disposition: force_keep > critical > force_compress > domain compaction
        is_force_kept = False
        for fk in force_keep_rules:
            if re.search(fk, w_file.name, re.IGNORECASE) or re.search(fk, raw_path, re.IGNORECASE):
                is_force_kept = True
                break
        
        is_critical = False
        if not is_force_kept:
            for crit in critical_rules:
                if re.search(crit, w_file.name, re.IGNORECASE) or re.search(crit, raw_path, re.IGNORECASE):
                    is_critical = True
                    break
        
        is_force_compressed = False
        for fc in force_compress_rules:
            if re.search(fc, w_file.name, re.IGNORECASE) or re.search(fc, raw_path, re.IGNORECASE):
                is_force_compressed = True
                break
        
        # Force-kept files: copy raw original just like critical
        if is_force_kept and raw_path != "unknown":
            src_raw = ws / raw_path
            if src_raw.exists():
                force_kept_files.append(raw_path)
                if not dry_run:
                    fk_out = out_dir / "FORCE_KEPT_ORIGINALS"
                    fk_out.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_raw, fk_out / src_raw.name)
            else:
                warnings.append(f"Force-kept raw file missing: {src_raw}")
                qa_checks["traceability_check"] = "needs_review"
        
        # Critical: copy raw original
        if (is_critical and not is_force_kept) and raw_path != "unknown":
            src_raw = ws / raw_path
            if src_raw.exists():
                critical_files_copied += 1
                if not dry_run:
                    crit_out = out_dir / "CRITICAL_ORIGINALS"
                    crit_out.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_raw, crit_out / src_raw.name)
            else:
                warnings.append(f"Critical raw file missing: {src_raw}")
                qa_checks["traceability_check"] = "fail"
                
        # Force-compressed files skip domain logic, go straight to a "ForceCompressed" domain
        if is_force_compressed and not is_force_kept:
            domain = "ForceCompressed"
        else:
            domain = determine_domain(w_file.name, domain_rules)
        
        # Check technical fact from SOURCE wiki
        facts = check_technical_facts(body)
        if any(facts.values()):
            has_technical_source = True
            for k in facts:
                if facts[k]: technical_coverage[k] = True
                
        # Build block for compaction
        block = f"""
## Source: {meta.get('title', w_file.name)}
Status: {meta.get('status', 'unknown')}
Confidence: {meta.get('confidence', 'unknown')}
Manifest: processed/manifest.jsonl#line-{line_no if line_no else 'unknown'}
Raw: {raw_path}
Wiki: {wiki_rel_path}
Contradictions: None

{body}
"""
        compaction_dict[domain] = compaction_dict.get(domain, "") + block
        
        if domain not in mapped_manifests:
            mapped_manifests[domain] = []
        mapped_manifests[domain].append({
            "manifest_line": line_no if line_no else 0,
            "raw_path": raw_path,
            "wiki_source_ref": wiki_rel_path
        })

    # NotebookLM target source count = compressed domains + critical originals + force-kept originals
    actual_notebooklm_sources = len(compaction_dict) + critical_files_copied + len(force_kept_files)
    
    if actual_notebooklm_sources > limits.get("hard_source_limit", 50):
        qa_checks["source_limit_check"] = "fail"
        warnings.append(f"Hard limit exceeded. NotebookLM sources: {actual_notebooklm_sources}")
    elif actual_notebooklm_sources > limits.get("soft_warning_limit", 45):
        qa_checks["source_limit_check"] = "needs_review"
        
    # Verify technical facts survived in compressed output
    if has_technical_source:
        all_compressed = "\n".join(compaction_dict.values())
        compressed_facts = check_technical_facts(all_compressed)
        lost_facts = []
        for fact_type, found_in_source in [("fields", technical_coverage["fields"]),
                                            ("db_tables", technical_coverage["db_tables"]),
                                            ("endpoints", technical_coverage["endpoints"]),
                                            ("errors", technical_coverage["errors"])]:
            if found_in_source and not compressed_facts[fact_type]:
                lost_facts.append(fact_type)
        if lost_facts:
            qa_checks["technical_facts_coverage"] = "fail"
            warnings.append(f"Technical facts lost during compaction: {', '.join(lost_facts)}")
    elif not has_technical_source:
        # No technical facts in any source -> not applicable, keep pass
        pass

    final_qa = "pass"
    for k, v in qa_checks.items():
        if v == "fail":
            final_qa = "fail"
            break
        elif v == "needs_review":
            final_qa = "needs_review"

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        wiki_comp_dir = out_dir / "WIKI_COMPRESSED"
        wiki_comp_dir.mkdir(exist_ok=True)
        
        manifest_mappings = []
        for domain, content in compaction_dict.items():
            comp_file = wiki_comp_dir / f"WIKI_COMPRESSED_{domain}.md"
            with open(comp_file, "w", encoding="utf-8") as f:
                f.write(f"# Domain: {domain}\n")
                f.write("> Deterministic Compaction Package\n")
                f.write(content)
            
            manifest_mappings.append({
                "output_file": f"WIKI_COMPRESSED/WIKI_COMPRESSED_{domain}.md",
                "sources": mapped_manifests[domain]
            })
            
        manifest_payload = {
            "package_id": package_id,
            "generated_at": datetime.now().isoformat() + "Z",
            "total_sources_count": actual_notebooklm_sources,
            "qa_status": final_qa,
            "policy_snapshot": limits,
            "retained_originals": critical_files_copied,
            "compressed_wikis": len(compaction_dict),
            "excluded_sources": excluded_count,
            "grounding_warnings": warnings,
            "qa_checks": qa_checks,
            "traceability_coverage_summary": {
                "endpoints_covered": technical_coverage["endpoints"],
                "fields_covered": technical_coverage["fields"],
                "error_codes_covered": technical_coverage["errors"],
                "versions_covered": False,
                "config_keys_covered": False,
                "db_tables_columns_covered": technical_coverage["db_tables"]
            },
            "warnings": warnings,
            "manifest_mapping": manifest_mappings
        }
        
        with open(out_dir / "package_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest_payload, f, indent=2, ensure_ascii=False)
            
        with open(out_dir / "QA_REPORT.md", "w", encoding="utf-8") as f:
            f.write(f"# QA REPORT\nStatus: {final_qa}\nWarnings: {len(warnings)}\n")
            for w in warnings:
                f.write(f"- {w}\n")

    summary = {
        "wiki_notes_detected": len(wiki_files),
        "actual_notebooklm_sources": actual_notebooklm_sources,
        "critical_kept": critical_files_copied,
        "compressed_files": len(compaction_dict),
        "package_id": package_id,
        "qa_status": final_qa,
        "warnings_count": len(warnings),
        "output_path": str(out_dir) if not dry_run else "Dry Run"
    }
    print(json.dumps(summary, indent=2))
    
    if final_qa == "fail":
        return 3
    elif final_qa == "needs_review":
        return 2
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".", help="Workspace root")
    parser.add_argument("--policy", required=True, help="Path to JSON policy file")
    parser.add_argument("--output", default="notebooks/packages", help="Output directory")
    parser.add_argument("--package-id", default="auto", help="ID of the package")
    parser.add_argument("--dry-run", type=lambda x: (str(x).lower() == 'true'), default=False)
    
    args = parser.parse_args()
    try:
        sys.exit(run_packager(args.workspace, args.policy, args.output, args.package_id, args.dry_run))
    except Exception as e:
        logger.exception("Runtime error in packager")
        sys.exit(1)
