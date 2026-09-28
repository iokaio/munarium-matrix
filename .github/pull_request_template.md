## What and why

<!-- One paragraph. Link the issue if there is one. -->

## Checks

- [ ] Every commit is signed off (`git commit -s`; the DCO, see CONTRIBUTING.md).
- [ ] `test.ps1` and `test.ps1 -Gates` pass locally; `boundaries.py` and `doclint.py` are green.
- [ ] New source files carry `SPDX-License-Identifier: Apache-2.0` on the first line; `check_license.py` is green.
- [ ] Documentation that states the changed behavior is updated in this pull request.

## Disclosure

Answer each; "none" is an answer.

1. **Third-party code** in this pull request (any file or fragment you did not write), with its license:
2. **Generated code** (what generated it, from what):
3. **AI-tool provenance** (which tools helped write this, and that you reviewed every line):
4. **Employer or contractual restrictions** on contributing this:

I have the right to submit every file in this pull request under the Apache License 2.0.

## Maintainer self-review

<!-- For a pull request the owner merges on their own review — the compensating control
     for a sole approver. -->

- [ ] Read the whole diff once more after CI went green, as a reviewer would.
- [ ] No credential, hostname, internal path, or private document entered the tree.
- [ ] `contract/` is untouched, or was re-vendored by the publisher, never edited.
