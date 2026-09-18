---- MODULE NLC_Cutover_T3 ----
EXTENDS Naturals, FiniteSets

CONSTANT NonLinearizable
VARIABLES phase, roots, votes, partitioned, crashed
vars == <<phase, roots, votes, partitioned, crashed>>

Init == /\ phase = "idle"
        /\ roots = {}
        /\ votes = {}
        /\ partitioned = FALSE
        /\ crashed = FALSE

VerifyCertificate == /\ phase = "idle"
                     /\ phase' = "cert_verified"
                     /\ UNCHANGED <<roots, votes, partitioned, crashed>>
BeginFence == /\ phase = "cert_verified" /\ ~crashed
              /\ phase' = "fence_preparing"
              /\ UNCHANGED <<roots, votes, partitioned, crashed>>
ConfirmFence == /\ phase = "fence_preparing" /\ ~crashed /\ ~partitioned
                /\ phase' = "fence_confirmed"
                /\ UNCHANGED <<roots, votes, partitioned, crashed>>
PrepareSlots == /\ phase = "fence_confirmed"
                /\ phase' = "slots_prepared"
                /\ UNCHANGED <<roots, votes, partitioned, crashed>>
VoteQ1 == /\ phase = "slots_prepared" /\ "Q1" \notin votes
          /\ votes' = votes \union {"Q1"}
          /\ UNCHANGED <<phase, roots, partitioned, crashed>>
VoteQ2 == /\ phase = "slots_prepared" /\ "Q2" \notin votes
          /\ votes' = votes \union {"Q2"}
          /\ UNCHANGED <<phase, roots, partitioned, crashed>>
PrepareRoot == /\ phase = "slots_prepared" /\ votes = {"Q1", "Q2"} /\ ~partitioned
               /\ phase' = "root_prepared" /\ roots' = {"R1"}
               /\ UNCHANGED <<votes, partitioned, crashed>>
Commit == /\ phase = "root_prepared" /\ roots = {"R1"}
          /\ phase' = "committed"
          /\ UNCHANGED <<roots, votes, partitioned, crashed>>
Retrieve == /\ phase = "committed"
            /\ phase' = "delivered"
            /\ UNCHANGED <<roots, votes, partitioned, crashed>>
CompetingCertificate == /\ phase = "cert_verified"
                        /\ UNCHANGED vars
Crash == /\ phase \notin {"idle", "delivered"} /\ ~crashed
         /\ crashed' = TRUE /\ UNCHANGED <<phase, roots, votes, partitioned>>
Retry == /\ crashed /\ crashed' = FALSE
         /\ UNCHANGED <<phase, roots, votes, partitioned>>
Partition == /\ phase \notin {"idle", "delivered"} /\ ~partitioned
             /\ partitioned' = TRUE /\ UNCHANGED <<phase, roots, votes, crashed>>
Heal == /\ partitioned /\ partitioned' = FALSE
        /\ UNCHANGED <<phase, roots, votes, crashed>>
CommitCompetingRoot == /\ NonLinearizable /\ phase \in {"committed", "delivered"}
                       /\ roots = {"R1"} /\ roots' = {"R1", "R2"}
                       /\ UNCHANGED <<phase, votes, partitioned, crashed>>

Next == VerifyCertificate \/ BeginFence \/ ConfirmFence \/ PrepareSlots \/ VoteQ1 \/ VoteQ2
        \/ PrepareRoot \/ Commit \/ Retrieve \/ CompetingCertificate \/ Crash \/ Retry
        \/ Partition \/ Heal \/ CommitCompetingRoot
Spec == Init /\ [][Next]_vars
UniqueRoot == Cardinality(roots) <= 1
====
