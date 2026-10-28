import argparse
from services.pipeline import create_job, run_job

def main():
    parser = argparse.ArgumentParser(description='Discover public dental business listings')
    parser.add_argument('--niche', default='dentists'); parser.add_argument('--city'); parser.add_argument('--state'); parser.add_argument('--limit', type=int, default=100); parser.add_argument('--resume', type=int)
    args = parser.parse_args()
    if args.resume:
        job_id = args.resume
    else:
        if not args.city or not args.state: parser.error('--city and --state are required')
        if not 1 <= args.limit <= 1000: parser.error('--limit must be between 1 and 1000')
        job_id = create_job(args.niche, args.city, args.state, 'OpenStreetMap', args.limit)
    print(f'Running job {job_id}', flush=True)
    run_job(job_id)
    print(f'Job {job_id} complete', flush=True)

if __name__ == '__main__': main()
