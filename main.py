import argparse
import github
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser(description="Utility for some Github stuff.")
    parser.add_argument(
        "--access-token",
        required=True,
        help="Personal access token. Generate it via Github 'Developer Settings'",
    )
    parser.add_argument("--org", help="If specified repo is assumed to be in an org")
    parser.add_argument("--repo", required=True, help="Repository to operate on")
    parser.add_argument(
        "--migrate-to", help="Repository to migrate *to*", default=None, type=str
    )
    parser.add_argument(
        "--create-test-issues",
        help="Create a bunch of test issues in repo-src. Use this to try out the tool beforehand!",
        action="store_true",
    )
    parser.add_argument(
        "--add-label",
        help="Adds given label to *all* issues in the repo",
        default=None,
        type=str,
    )
    args = parser.parse_args()

    g = github.Github(args.access_token)
    if args.org:
        org = g.get_organization(args.org)
        repo = org.get_repo(args.repo)
    else:
        repo = g.get_repo(args.repo)

    if args.create_test_issues:
        for i in range(0, 3):
            print(f"creating test issue {i}..")
            repo.create_issue(
                "Test issue %d" % i, "Test issue body %d" % i, labels=["test-label"]
            )
        print("test issue generation done!")

    if args.add_label is not None:
        for issue in repo.get_issues():
            for label in args.add_label.split(","):
                label = label.strip()
                print(f"adding label '{label}' to issue {issue.number}..")
                issue.add_to_labels(label)
        print("adding labels done!")

    if args.migrate_to is not None:
        if args.org:
            org = g.get_organization(args.org)
            repo_dst = org.get_repo(args.repo)
        else:
            repo_dst = g.get_repo(args.repo)

        for issue in repo.get_issues():
            if issue.state != "open":
                print(f"skipping issue {issue.number} because it is not open")
                continue

            print(f"migrating issue {issue.number} to {args.migrate_to}..")
            # query labels before migration
            labels = issue.labels.copy()

            # pygithub can't migrate :(
            process = subprocess.run(
                [
                    "gh",
                    "issue",
                    "transfer",
                    str(issue.number),
                    args.migrate_to,
                    "--repo",
                    args.repo,
                ],
                check=True,
                capture_output=True,
            )
            if process.returncode != 0:
                print(f"failed to transfer issue {issue.number} to {args.migrate_to}!")
                print(process.stdout)
                print(process.stderr)
                return
            issue_number_in_dst = process.stdout.decode("utf-8").split("/")[-1]
            issue_number_in_dst = int(issue_number_in_dst)

            print(
                f"successfully transfered. Re-adding labels to issue #{issue_number_in_dst} in {repo_dst.name}..."
            )
            dst_issue = repo_dst.get_issue(issue_number_in_dst)
            dst_issue.set_labels(*labels)

        print("migration done!")


if __name__ == "__main__":
    main()
