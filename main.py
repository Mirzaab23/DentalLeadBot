import argparse
from services.pipeline import create_job, run_job

def main():
    parser = argparse.ArgumentParser(description='Discover public business listings')
    parser.add_argument('--niche'); parser.add_argument('--city'); parser.add_argument('--state',default=''); parser.add_argument('--country',default='United States'); parser.add_argument('--limit', type=int, default=100); parser.add_argument('--source', choices=['All sources', 'Google Maps', 'OpenStreetMap', 'Yelp'], default='All sources'); parser.add_argument('--resume', type=int)
    args = parser.parse_args()
    if args.resume:
        job_id = args.resume
    else:
        if not args.niche or not args.city or not args.country: parser.error('--niche, --city and --country are required')
        if not 1 <= args.limit <= 1000: parser.error('--limit must be between 1 and 1000')
        job_id = create_job(args.niche, args.city, args.state, args.source, args.limit, country=args.country)
    print(f'Running job {job_id}', flush=True)
    run_job(job_id)
    print(f'Job {job_id} complete', flush=True)

if __name__ == '__main__': main()
