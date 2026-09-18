---- MODULE NLC_Recovery_T3 ----
EXTENDS Naturals, FiniteSets

CONSTANTS NonLinearizable, OldScopeFenced, UnknownAsSuccess, DeterministicOutput
VARIABLES phase, adapter, requests, outputs, effects, delayedOldEffect, partitioned, crashed
vars == <<phase, adapter, requests, outputs, effects, delayedOldEffect, partitioned, crashed>>
Adapters == {"IDEMPOTENT", "ESCROWED", "FENCED", "UNOBSERVABLE"}

Init == /\ phase = "unused" /\ adapter = "NONE"
        /\ requests = {} /\ outputs = {} /\ effects = {} /\ delayedOldEffect = FALSE
        /\ partitioned = FALSE /\ crashed = FALSE
ChooseAdapter(a) == /\ phase = "unused" /\ a \in Adapters
                    /\ phase' = "settlement" /\ adapter' = a /\ requests' = {"Q1"}
                    /\ UNCHANGED <<outputs, effects, delayedOldEffect, partitioned, crashed>>
CompetingRequest == /\ phase = "settlement" /\ "Q2" \notin requests
                    /\ requests' = requests \union {"Q2"}
                    /\ UNCHANGED <<phase, adapter, outputs, effects, delayedOldEffect, partitioned, crashed>>
SettlementKnown == /\ phase = "settlement" /\ adapter # "UNOBSERVABLE" /\ ~partitioned
                   /\ phase' = "prepared"
                   /\ UNCHANGED <<adapter, requests, outputs, effects, delayedOldEffect, partitioned, crashed>>
UnknownHold == /\ phase = "settlement" /\ adapter = "UNOBSERVABLE" /\ ~UnknownAsSuccess
               /\ phase' = "recovery_hold"
               /\ UNCHANGED <<adapter, requests, outputs, effects, delayedOldEffect, partitioned, crashed>>
UnknownSuccess == /\ phase = "settlement" /\ adapter = "UNOBSERVABLE" /\ UnknownAsSuccess
                  /\ phase' = "prepared"
                  /\ UNCHANGED <<adapter, requests, outputs, effects, delayedOldEffect, partitioned, crashed>>
SafeCommit == /\ phase = "prepared" /\ ~NonLinearizable /\ DeterministicOutput
              /\ (OldScopeFenced \/ adapter # "UNOBSERVABLE")
              /\ phase' = "committed" /\ outputs' = {"O1"} /\ effects' = {"E1"}
              /\ UNCHANGED <<adapter, requests, delayedOldEffect, partitioned, crashed>>
UnsafeCommit == /\ phase = "prepared"
                /\ (NonLinearizable \/ ~DeterministicOutput \/ ~OldScopeFenced \/ (adapter = "UNOBSERVABLE" /\ UnknownAsSuccess))
                /\ phase' = "committed"
                /\ outputs' = IF (NonLinearizable \/ ~DeterministicOutput) THEN {"O1", "O2"} ELSE {"O1"}
                /\ effects' = IF (NonLinearizable \/ ~OldScopeFenced \/ (adapter = "UNOBSERVABLE" /\ UnknownAsSuccess)) THEN {"E1", "E2"} ELSE {"E1"}
                /\ UNCHANGED <<adapter, requests, delayedOldEffect, partitioned, crashed>>
DelayedOldEffect == /\ phase \in {"prepared", "committed"} /\ ~delayedOldEffect
                    /\ delayedOldEffect' = TRUE
                    /\ UNCHANGED <<phase, adapter, requests, outputs, effects, partitioned, crashed>>
Retrieve == /\ phase = "committed" /\ phase' = "delivered"
            /\ UNCHANGED <<adapter, requests, outputs, effects, delayedOldEffect, partitioned, crashed>>
Crash == /\ phase \in {"settlement", "prepared", "committed"} /\ ~crashed
         /\ crashed' = TRUE /\ UNCHANGED <<phase, adapter, requests, outputs, effects, delayedOldEffect, partitioned>>
SlotRetry == /\ crashed /\ crashed' = FALSE
             /\ UNCHANGED <<phase, adapter, requests, outputs, effects, delayedOldEffect, partitioned>>
Partition == /\ phase \in {"settlement", "prepared"} /\ ~partitioned
             /\ partitioned' = TRUE /\ UNCHANGED <<phase, adapter, requests, outputs, effects, delayedOldEffect, crashed>>
Heal == /\ partitioned /\ partitioned' = FALSE
        /\ UNCHANGED <<phase, adapter, requests, outputs, effects, delayedOldEffect, crashed>>

Next == (\E a \in Adapters: ChooseAdapter(a)) \/ CompetingRequest \/ SettlementKnown \/ UnknownHold \/ UnknownSuccess
        \/ SafeCommit \/ UnsafeCommit \/ DelayedOldEffect \/ Retrieve \/ Crash \/ SlotRetry \/ Partition \/ Heal
Spec == Init /\ [][Next]_vars
UniqueOutput == Cardinality(outputs) <= 1
UniqueEffect == Cardinality(effects) <= 1
====
