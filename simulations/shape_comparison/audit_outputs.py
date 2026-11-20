"""Cross-check saved applied fields, checkpoint lineage and summary provenance."""
import hashlib
from simulate import BASE, MU0, MS, dump, json, np, ovf, table, geometry


def audit():
    rows=[]
    for summary_path in sorted((BASE/'runs').glob('*/summary.json')):
        folder=summary_path.parent
        saved=json.loads(summary_path.read_text(encoding='utf-8'))
        config=saved['config']
        checks={}
        if (folder/'input.mif').exists():
            # The generator hashes UTF-8 text with LF; Windows writes CRLF on disk.
            checks['mif_normalized_text_hash']=hashlib.sha256((folder/'input.mif').read_text(encoding='utf-8').encode()).hexdigest()==config['mif_sha256']
            initial=ovf(folder/'initial.omf')[0]
            checks['initial_hash']=hashlib.sha256(np.asarray(initial,dtype='<f8').tobytes()).hexdigest()==config['initial_sha256']
            if config['predecessor']:
                from pathlib import Path
                source=Path(config['predecessor'])
                checks['predecessor_hash']=source.exists() and hashlib.sha256(source.read_bytes()).hexdigest()==config['predecessor_sha256']
            data=table(next(folder.glob('*.odt')))
            stage=data['Oxs_TimeDriver::Stage'].astype(int)
            checks['stage_count']=set(stage)==set(range(len(config['fields_T'])))
            if not config['static']:
                actual=np.array([data['Oxs_UZeeman:zeeman:Bz'][np.flatnonzero(stage==i)[-1]]/1000 for i in range(len(config['fields_T']))])
                checks['actual_applied_fields']=bool(np.max(np.abs(actual-config['fields_T']))<1e-10)
                checks['zero_transverse_field']=bool(np.max(np.abs(data['Oxs_UZeeman:zeeman:Bx']))<1e-10 and np.max(np.abs(data['Oxs_UZeeman:zeeman:By']))<1e-10)
                g,mask,_=geometry(config['shape'],config['cell_nm'])
                zeeman_errors=[]
                for record in saved['stages']:
                    expected=-MS*g['volume_m3']*record['b_T']*record['mean_m'][2]
                    zeeman_errors.append(abs(expected-record['energy_J']['Oxs_UZeeman:zeeman:Energy']))
                checks['zeeman_from_field_and_m']=max(zeeman_errors)<1e-25
        else:
            checks['aggregate_stage_count']=len(saved['stages'])==len(config['fields_T'])
            checks['aggregate_fields']=all(abs(r['b_T']-b)<1e-10 for r,b in zip(saved['stages'],config['fields_T']))
            checks['aggregate_sequence']=[r['stage'] for r in saved['stages']]==list(range(len(saved['stages'])))
            lineage_ok=True
            last_file=config['predecessor']
            previous_source=None
            for record in saved['stages']:
                part_dir=BASE/'runs'/record['source_run']
                part=json.loads((part_dir/'summary.json').read_text(encoding='utf-8'))
                source_file=(folder/record['spin_file']).resolve()
                lineage_ok &= source_file.exists()
                if record['source_run']!=previous_source:
                    from pathlib import Path
                    declared=part['config']['predecessor']
                    lineage_ok &= (declared is None and last_file is None) or (declared is not None and last_file is not None and Path(declared).resolve()==Path(last_file).resolve())
                last_file=source_file
                previous_source=record['source_run']
            checks['aggregate_checkpoint_lineage']=bool(lineage_ok)
        row=dict(run_id=folder.name,checks=checks,passed=all(checks.values()))
        if (folder/'input.mif').exists():
            row['mif_file_sha256']=hashlib.sha256((folder/'input.mif').read_bytes()).hexdigest()
        rows.append(row)
    result=dict(audited_runs=len(rows),checks=sum(len(r['checks']) for r in rows),
                all_passed=all(r['passed'] for r in rows),runs=rows)
    dump(BASE/'analysis/output_audit.json',result)
    if not result['all_passed']:
        raise RuntimeError(str([r for r in rows if not r['passed']]))
    print(f'OUTPUT AUDIT {len(rows)} runs, {result["checks"]} checks passed',flush=True)
    return result


if __name__=='__main__':
    audit()
