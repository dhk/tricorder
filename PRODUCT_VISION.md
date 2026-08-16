# Tricorder Product Vision

## Vision

Tricorder helps teams understand how well they build and systematically raise the standard.

The product is not trying to decide whether a team chose the right business problem. It assumes people are working together toward a common purpose and focuses on the capability that determines whether they can build that purpose well.

## The problem

Teams accumulate capability unevenly.

Some standards live in code. Some live in CI. Some live in review comments. Some live in documentation. Some live in the heads of experienced people. Some are expressed only when something goes wrong.

This makes quality fragile. The team may be good because the right person notices the right thing at the right time rather than because the system reliably carries what the team knows.

Repositories and review histories contain unusually rich evidence of this hidden operating system. They show what gets built, what gets corrected, what repeatedly causes friction, what reviewers care about, and what eventually becomes accepted.

Tricorder turns that evidence into an inspectable model of team capability.

## What good looks like

A strong team should be able to see:

- where it is consistently strong;
- where quality depends on individual heroics;
- where the same correction is being paid for repeatedly;
- where repository structure or code quality creates friction;
- where standards are implicit, inconsistent, or missing;
- where accountability is concentrated or unclear;
- where education would raise judgment;
- where workflow changes would make quality easier;
- where deterministic tooling or automation should carry repeated knowledge;
- whether those interventions actually improve the team over time.

## The improvement loop

Tricorder's long-term product loop is:

**observe capability → identify strengths, variance, and gaps → propose interventions → encode appropriate improvements → observe whether capability improves**

The intervention should fit the problem.

Sometimes the answer is education. Sometimes it is a skill. Sometimes it is a workflow hook. Sometimes it is clearer accountability. Sometimes it is repository work. Sometimes it is a deterministic check. Sometimes it is automation. Sometimes the right answer is to leave judgment with people.

The goal is not maximal standardization. The goal is a stronger team.

## The relationship to the other products

The three products have distinct organizing centers:

- **Wingman** is about the person.
- **Work Ledger** is about the work.
- **Tricorder** is about the team's capability to build well together.

Work Ledger can reveal how work is produced. Tricorder reveals how the team's standards, repositories, review processes, and operating mechanisms shape the quality of what gets produced.

Together they can eventually answer complementary questions: how we work, and how we make sure we build well together.

## What Tricorder does not aspire to be

Tricorder is not an employee ranking system, performance-review system, productivity scoreboard, or surveillance product.

It is not a substitute for live review.

It is not a generic engineering metrics dashboard.

It does not claim to determine whether a product strategy is correct or whether a team is building the right thing in the market.

It is a capability-improvement system for teams that want to build well.
