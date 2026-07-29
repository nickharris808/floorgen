# CLAIMS-MAP — `floorgen`

**Tag: CLEAN.** This package does not practise any claim in the associated patent family.

## The boundary

Every method independent in the family terminates in a **physical actuation step**. The step this
package deliberately does not take is the one the nearest claim family recites explicitly:
**provisioning resources at a computed floor, and refusing to admit work below it.**

| `floorgen` does | `floorgen` does not |
|---|---|
| enumerate a declared, finite situation space | observe any running system |
| count the distinct answers a spec demands | provision, size, or allocate anything |
| report that count as a lower bound on state | refuse or admit work on the basis of it |
| verify a proposed encoding by exhaustive check | install, bind, or enforce that encoding |
| prove a budget cannot meet a spec | act on that proof |

## The nearest claim family, and the step not taken

The family includes claims of the shape *derive a state floor from a faithful-observation
specification, **provision at that floor**, and **refuse operation below it***. The derivation step
resembles what this package does, and the resemblance is not accidental — the mathematics is the
same, and it is elementary mathematics that predates all of it.

The claims are not to the pigeonhole argument. They are to the **apparatus that acts on it**.
`floorgen` prints a number and exits. It has no interface to a resource manager, no admission
path, and no mechanism by which its exit code could withhold anything. A user who wires
`floorgen impossible` into a deployment gate is performing the actuation step themselves.

## On novelty

This package makes **no novelty claim whatsoever**. Pigeonhole lifted pointwise is textbook, the
statement is in every report the tool emits, and the worked recoveries are chosen precisely so
that each floor can be checked by hand without the tool. What is contributed here is a careful
exact count with explicit refusals, not a result.

## Provenance

Written for this release. The seven worked recoveries are constructed for the package; none is
extracted from a licensed implementation, and the package reads no internal corpus.
