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
    parser.add_argument("--repo", required=True, help="Repository to operate on")
    parser.add_argument(
        "--migrate-to", help="Repository to migrate *to*", default=None, type=str
    )
    parser.add_argument(
        "--create-test-issues",
        help="Create a N test issues in repo-src. Use this to try out the tool beforehand!",
        default=None,
        type=int,
    )
    parser.add_argument(
        "--add-label",
        help="Adds given label to *all* issues in the repo",
        default=None,
        type=str,
    )
    parser.add_argument(
        "--maximum-issues",
        help="Limits the number of issues to migrate",
        default=None,
        type=int,
    )
    args = parser.parse_args()

    g = github.Github(args.access_token)
    repo = g.get_repo(args.repo)

    if args.create_test_issues is not None:
        for i in range(0, args.create_test_issues):
            print(f"creating test issue {i}..")
            repo.create_issue(
                "Test issue %d" % i, "Test issue body %d" % i, labels=["test-label"]
            )
        print("test issue generation done!")

    if args.migrate_to is not None:
        repo_dst = g.get_repo(args.migrate_to)

        issues_transferred = 0

        issues = []
        for issue in repo.get_issues(direction="asc"):
            if issue.state != "open":
                print(f"skipping issue {issue.number} because it is not open")
                continue

            if issue.pull_request is not None:
                print(f"skipping issue {issue.number} because it is a PR")
                continue

            issues.append(issue)

        print(f"found {len(issues)} issues to transfer")

        for issue in issues:
            print(f"\t#{issue.number}: {issue.title}")

        for issue in issues:
            if args.maximum_issues is not None:
                if issues_transferred >= args.maximum_issues:
                    print("transfered maximum number of issues, stopping..")
                    return

            issues_transferred += 1
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
                f"successfully transfered. Re-adding {labels} to issue #{issue_number_in_dst} in {repo_dst.name}..."
            )
            dst_issue = repo_dst.get_issue(issue_number_in_dst)
            dst_issue.set_labels(*labels)

            if args.add_label is not None:
                for label in args.add_label.split(","):
                    label = label.strip()
                    print(f"adding extra label '{label}' to issue {issue_number_in_dst}..")
                    dst_issue.add_to_labels(label)

        print("migration done!")


if __name__ == "__main__":
    main()
