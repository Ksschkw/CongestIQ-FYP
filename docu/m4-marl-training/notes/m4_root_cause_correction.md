# M4 root cause correction: the RL policy never controlled cwnd

Author: Okafor Kosisochukwu Johnpaul
Date: 3 October 2026
Status: correction of the explanation recorded in `m4_as_built.md`, `m4_experiments.md`
and `m4_observations.md`

## Why I wrote this note

My earlier M4 notes say the multi-agent evaluation failed because a custom
congestion control class named NoOpTcpCongestion was rejected by ns-3. I wrote
that the rejection happened because the class inherited from TcpCongestionOps
instead of TcpSocketBase, and that ns-3 therefore fell back to TCP CUBIC. I
wrote that explanation from memory of how ns-3 usually works, and I did not
check it against the ns-3 source in my own tree.

When I reopened the project to repair it, I read the source. The real cause is
different, simpler, and testable. This note records what I found, how I proved
it, and what I changed.

## What the earlier explanation assumed

The earlier explanation treated the `SocketType` attribute of the TCP layer
four protocol (`TcpL4Protocol`) as a socket factory that only accepts a subclass
of `TcpSocketBase`. Under that assumption, assigning a `TcpCongestionOps`
subclass to `SocketType` is a type error, and ns-3 quietly falls back to the
default algorithm.

## What I actually found in the source

I read `src/internet/model/tcp-l4-protocol.cc`. The `GetTypeId` function declares
the attribute like this:

```cpp
.AddAttribute("SocketType",
              "Socket type of TCP objects.",
              TypeIdValue(TcpCubic::GetTypeId()),
              MakeTypeIdAccessor(&TcpL4Protocol::m_congestionTypeId),
              MakeTypeIdChecker())
```

The attribute is stored in a member named `m_congestionTypeId`, and its default
value is `TcpCubic`, which is a `TcpCongestionOps` subclass. I then read how a
socket is created:

```cpp
ObjectFactory congestionAlgorithmFactory;
congestionAlgorithmFactory.SetTypeId(congestionTypeId);
Ptr<TcpCongestionOps> algo = congestionAlgorithmFactory.Create<TcpCongestionOps>();
```

So `SocketType` is the TypeId of the congestion control operations that each new
socket receives. It is not a socket class. This means NoOpTcpCongestion, which
inherits from `TcpCongestionOps`, is exactly the right kind of class for this
attribute. The class itself was never the problem.

The actual problem is when the attribute was set. In the original
`marl-multi-sim.cc`, the code did this:

```cpp
NodeContainer senders, receivers, routers;
senders.Create (nAgents);

for (uint32_t i = 0; i < senders.GetN (); ++i)
  {
    Config::Set ("/NodeList/" + std::to_string (senders.Get (i)->GetId ()) +
                 "/$ns3::TcpL4Protocol/SocketType",
                 TypeIdValue (NoOpTcpCongestion::GetTypeId ()));
  }

// ... later ...
InternetStackHelper stack;
stack.Install (senders);
```

Nodes are created first, but the `TcpL4Protocol` object is only added to a node
when `InternetStackHelper::Install` runs. At the time of the `Config::Set`
calls, a node has a name in the `/NodeList/` path but no `TcpL4Protocol` child,
so the path matches nothing.

## Why nothing was reported

I expected ns-3 to complain when a configuration path matches nothing. I read
`src/core/model/config.cc` to check. The public function is:

```cpp
void
Set(std::string path, const AttributeValue& value)
{
    ConfigImpl::Get()->Set(path, value);
}
```

and the implementation is:

```cpp
void
ConfigImpl::Set(std::string path, const AttributeValue& value)
{
    std::string root;
    std::string leaf;
    ParsePath(path, &root, &leaf);
    MatchContainer container = LookupMatches(root);
    container.Set(leaf, value);
}
```

`MatchContainer::Set` then does:

```cpp
for (auto tmp = Begin(); tmp != End(); ++tmp)
  {
    Ptr<Object> object = *tmp;
    object->SetAttribute(name, value);
  }
```

When the container is empty, the loop body never runs. Nothing is printed and
nothing is set. The configuration call is a silent no-op. This is the behaviour
that hid the bug.

The result is that every sender socket was created with the ns-3 default
congestion control, TCP CUBIC. The Python environment still wrote a new
congestion window into the socket state every 100 milliseconds, and the TCP
stack still ran native CUBIC on every acknowledgment in between. CUBIC's
per-acknowledgment changes therefore dominated the policy's coarse changes. The
evaluation numbers were CUBIC's numbers.

## Why the baselines and the single agent did work

The M5 baseline program, `scratch/two-flow-baseline.cc`, sets the same
attribute, but it does so after `internet.Install (senders)`:

```cpp
InternetStackHelper internet;
internet.Install (senders);
// ...
for (uint32_t i = 0; i < senders.GetN (); ++i)
  {
    Config::Set ("/NodeList/" + ... + "/$ns3::TcpL4Protocol/SocketType",
                 TypeIdValue (tcpTid));
  }
```

At that point the `TcpL4Protocol` object exists, so the path matches and the
attribute is set correctly. That is why the baselines behaved as expected.

The single-agent program, `contrib/ns3-gym/examples/rl-tcp/sim.cc`, used a
different mechanism again:

```cpp
Config::SetDefault ("ns3::TcpL4Protocol::SocketType",
                    TypeIdValue (TcpRlTimeBased::GetTypeId()));
```

`SetDefault` changes the initial value of the attribute for every object created
after the call. Because this ran before the internet stack was installed, every
socket created later received the RL congestion control class. This is the same
kind of assignment as the multi-agent case, and it worked. That is consistent
with `SocketType` being a congestion-ops TypeId.

## The fix I applied

1. I moved the `SocketType` assignment so it runs after
   `InternetStackHelper::Install (senders)`.
2. I changed the call from `Config::Set` to `Config::SetFailSafe`, which returns
   `false` when no object matches, and I abort the program if that happens. A
   silent fallback to TCP CUBIC can no longer occur.
3. I added a public getter, `TcpSocketBase::GetCongestionControlAlgorithm()`, to
   `src/internet/model/tcp-socket-base.{h,cc}`. This mirrors the existing
   `GetTcpState()` patch and lets a simulation ask a live socket which congestion
   control object is attached to it.
4. The multi-agent program now prints the attached algorithm name for every
   sender socket and aborts if it is not `NoOpTcpCongestion`.

The relevant part of the fixed `marl-multi-sim.cc` is:

```cpp
InternetStackHelper stack;
stack.Install (senders);
stack.Install (receivers);
stack.Install (routers);

for (uint32_t i = 0; i < senders.GetN (); ++i)
  {
    std::string path = "/NodeList/" + std::to_string (senders.Get (i)->GetId ()) +
                       "/$ns3::TcpL4Protocol/SocketType";
    bool ok = Config::SetFailSafe (path, TypeIdValue (NoOpTcpCongestion::GetTypeId ()));
    NS_ABORT_MSG_UNLESS (ok, "Could not attach NoOpTcpCongestion at " << path
                         << "; the RL policy would not own cwnd.");
  }
```

## How I proved the fix

I ran the program and read the printed line for each sender. It says:

```
[MarlMulti] sender 0 congestion control = NoOpTcpCongestion
[MarlMulti] sender 1 congestion control = NoOpTcpCongestion
```

A separate test, described in `m4_control_verification.md`, runs the same
topology with constant actions and shows that the congestion window follows the
actions instead of following CUBIC.

## What this means for the report

The submitted report explains the failure as an inheritance mismatch between
`TcpCongestionOps` and `TcpSocketBase`. In ns-3 as configured in this project,
that is not what happens. The accurate statement is that the configuration call
was made before the object it targeted existed, and `Config::Set` does not report
a miss. I will keep this correction with the other notes so the two explanations
are not confused later.
