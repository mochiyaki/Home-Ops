import { useEffect, useRef, useState } from "react";
import { health, mintLiveSession, mintVoiceSession, findProviders } from "./api.js";
import { runTurn, watchCall } from "./agent.js";
import { getCall, getCallDetail, getTranscript, listCalls } from "./api.js";
import { CallOverlay } from "./components/CallOverlay.jsx";
import {
  captureFrame,
  houseSnapshot,
  pickRoom,
  readDrawing,
  roomLabel,
  uid,
} from "./house.js";
import { Icon } from "./components/Icons.jsx";
import { IPhoneFrame } from "./components/IPhoneFrame.jsx";
import {
  injectOpsContext,
  speakOps,
  startOpsVoice,
  stopOpsVoice,
} from "./voice.js";
import HomeScreen from "./screens/HomeScreen.jsx";
import InventoryScreen from "./screens/InventoryScreen.jsx";
import ItemScreen from "./screens/ItemScreen.jsx";
import ProjectsScreen from "./screens/ProjectsScreen.jsx";
import JobScreen from "./screens/JobScreen.jsx";
import IssueScreen from "./screens/IssueScreen.jsx";
import ChatScreen from "./screens/ChatScreen.jsx";

const NAV = [
  { id: "home", label: "Home", icon: "home" },
  { id: "inventory", label: "Inventory", icon: "box" },
  { id: "projects", label: "Projects", icon: "folder" },
  { id: "chat", label: "Ops", icon: "chat" },
];

function issueText(data, house) {
  const room = data.roomId ? roomLabel(house, data.roomId) : "";
  return [data.notes || data.title, room, data.budget && `Budget ${data.budget}`, data.when]
    .filter(Boolean)
    .join(". ");
}

export default function App({ houseStore }) {
  const { house, setHouse } = houseStore;
  const [screen, setScreen] = useState("home");
  const [itemId, setItemId] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [issueSeed, setIssueSeed] = useState("");
  const [fileError, setFileError] = useState("");
  const [live, setLive] = useState(false);
  const [chat, setChat] = useState("");
  const [transcript, setTranscript] = useState([]);
  const [call, setCall] = useState("");
  const [mediaError, setMediaError] = useState("");
  const [apiState, setApiState] = useState({ ok: false, mock: false });
  const [busy, setBusy] = useState(false);
  const [voiceState, setVoiceState] = useState("idle");
  const [voiceMode, setVoiceMode] = useState(null);
  const [voiceError, setVoiceError] = useState("");
  const [liveCall, setLiveCall] = useState(null);
  const [callTurns, setCallTurns] = useState([]);
  const dismissedCallsRef = useRef(new Set());

  const videoRef = useRef(null);
  const photoRef = useRef(null);
  const stageRef = useRef(null);
  const streamRef = useRef(null);
  const pollStopRef = useRef(null);
  const houseRef = useRef(house);
  houseRef.current = house;
  const jobIdRef = useRef(jobId);
  jobIdRef.current = jobId;
  const voiceModeRef = useRef(null);
  const voiceLiveRef = useRef(false);
  const agentRef = useRef({
    askedOnce: false,
    pendingBrief: null,
    brief: null,
    providers: [],
    callCount: 0,
    calledPhones: new Set(),
    stopped: false,
    lastCallId: null,
  });

  useEffect(() => {
    health()
      .then((data) => setApiState({ ok: true, mock: Boolean(data.mock) }))
      .catch(() => setApiState({ ok: false, mock: false }));
    return () => {
      pollStopRef.current?.();
      stopMedia();
      stopOpsVoice();
    };
  }, []);

  useEffect(() => {
    stageRef.current?.scrollTo({ top: 0 });
  }, [screen, itemId, jobId]);

  // The Ops voice agent runs server-side, so calls it places never pass
  // through this browser. Poll the shared history so they still show up here.
  const announcedRef = useRef(new Set());
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const calls = await listCalls(5);
        if (stop || !Array.isArray(calls)) return;
        const active = calls.find(
          (c) => c.state === "dialing" || c.state === "in-call"
        );
        if (active) {
          const shop = active.shop_name || "a shop";
          setCall(
            active.state === "dialing"
              ? `Calling ${shop}…`
              : `On the line with ${shop}`
          );
          if (!dismissedCallsRef.current.has(active.id)) {
            setLiveCall((cur) =>
              cur && cur.id === active.id ? cur : { ...active, turnsFrom: "poll" }
            );
          }
        }
        calls
          .filter((c) => c.state === "done" && !announcedRef.current.has(c.id))
          .forEach((c) => {
            announcedRef.current.add(c.id);
            const line = c.quote || c.summary;
            if (line) {
              addTranscript("HomeOps", `${c.shop_name || "Shop"}: ${line}`);
              setCall(c.booked ? "Booked" : "Quote in — not booked");
            }
          });
      } catch {
        /* backend not reachable; the local flow still works */
      }
    };
    // Seed the announced set so a page load does not replay old calls.
    listCalls(20)
      .then((calls) => {
        if (Array.isArray(calls)) {
          calls.forEach((c) => announcedRef.current.add(c.id));
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!stop) tick();
      });
    const timer = setInterval(tick, 3000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, []);

  // Follow the active outbound call: stream its transcript into the overlay.
  const liveCallId = liveCall?.id;
  const liveCallOver = liveCall?.state === "done" || liveCall?.state === "failed";
  useEffect(() => {
    if (!liveCallId || liveCallOver) return undefined;
    let stop = false;
    const follow = async () => {
      try {
        const [status, turns] = await Promise.all([
          getCall(liveCallId),
          getTranscript(liveCallId),
        ]);
        if (stop) return;
        setCallTurns(Array.isArray(turns) ? turns : []);
        setLiveCall((cur) =>
          cur && cur.id === liveCallId ? { ...cur, ...status } : cur
        );
      } catch {
        /* transient — keep polling */
      }
    };
    follow();
    const timer = setInterval(follow, 1200);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [liveCallId, liveCallOver]);

  // Deep link for demos: /?call=<id> replays that call in the overlay.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("call");
    if (!id) return;
    getCallDetail(id)
      .then((detail) => {
        setLiveCall(detail);
        setCallTurns(detail.transcript || []);
      })
      .catch(() => {});
  }, []);

  const closeCallOverlay = () => {
    if (liveCall) dismissedCallsRef.current.add(liveCall.id);
    setLiveCall(null);
    setCallTurns([]);
  };

  const addTranscript = (who, text) => {
    setTranscript((rows) => [...rows, { who, text }]);
  };

  const patchProject = (id, fn) => {
    setHouse((h) => ({
      ...h,
      projects: (h.projects || []).map((p) => (p.id === id ? fn(p) : p)),
    }));
  };

  const createIssueJob = (data) => {
    const id = uid();
    const job = {
      id,
      title: data.title,
      kind: data.kind || "repair",
      status: "intake",
      budget: data.budget || "",
      notes: data.notes || "",
      roomId: data.roomId || "",
      bids: [],
    };
    setHouse((h) => ({ ...h, projects: [job, ...(h.projects || [])] }));
    setJobId(id);
    jobIdRef.current = id;
    return job;
  };

  const onPhoto = async (event) => {
    const file = event.target.files?.[0];
    setFileError("");
    if (!file) return;
    try {
      const dataUrl = await readDrawing(file);
      const room = pickRoom(houseRef.current, file.name);
      const id = uid();
      setHouse((h) => ({
        ...h,
        assets: [
          ...h.assets,
          {
            id,
            roomId: room?.id,
            category: "appliance",
            brand: "",
            model: "",
            photoDataUrl: dataUrl,
          },
        ],
      }));
      setItemId(id);
      setScreen("item");
    } catch {
      setFileError("Could not read that photo.");
    }
    event.target.value = "";
  };

  const stopMedia = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const startLive = async () => {
    setLive(true);
    setMediaError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
    } catch {
      setMediaError("Camera denied — typing still works.");
    }
    try {
      const session = await mintLiveSession();
      if (session.mock) setApiState((s) => ({ ...s, mock: true }));
    } catch {
      /* chat still works */
    }
  };

  const stopLive = () => {
    setLive(false);
    stopMedia();
  };

  const startPoll = (id, shop) => {
    pollStopRef.current?.();
    pollStopRef.current = watchCall(id, {
      onState: (data) => {
        if (data.mock) setApiState((s) => ({ ...s, mock: true }));
        if (data.state === "dialing") setCall(`Calling ${shop?.name || "shop"}…`);
        if (data.state === "in-call") setCall("On the line as HomeOps");
        if (data.state === "done")
          setCall(data.booked ? `Booked — ${shop?.name || "shop"}` : "Quote in — not booked");
        if (data.state === "failed") setCall("No answer");
      },
      onDone: (data) => {
        const quote = data.quote || data.summary;
        if (!quote) return;
        const booked = Boolean(data.booked);
        const pid = jobIdRef.current;
        if (pid) {
          patchProject(pid, (p) => ({
            ...p,
            status: booked ? "booked" : p.status,
            bids: (p.bids || []).map((b) =>
              b.phone === shop.phone
                ? { ...b, quote, booked, appointment: data.appointment || "" }
                : b
            ),
          }));
        }
        addTranscript("HomeOps", `${shop?.name}: ${quote}`);
        if (booked) {
          injectOpsContext(
            `Booked: ${shop?.name}, ${data.appointment || "time confirmed on the call"}, ${quote}. Tell the homeowner who is coming and when.`
          );
          return;
        }
        injectOpsContext(
          `Quote from ${shop?.name}: ${quote}. Not booked — it did not fit. Trying the next shop.`
        );
        // Autonomous outreach: keep calling down the list until something books.
        const agent = agentRef.current;
        const called = agent.calledPhones || new Set();
        const next = agent.providers.find((p) => p.phone && !called.has(p.phone));
        if (next && agent.callCount < 3 && !agent.stopped) {
          addTranscript("HomeOps", `Trying the next shop: ${next.name}.`);
          handleTurn("try the next shop");
        }
      },
      onError: (err) => setCall(err.message),
    });
  };

  const toolCtx = () => ({
    house: houseRef.current,
    agent: agentRef.current,
    onActivity: () => {},
    onMock: (flag) => flag && setApiState((s) => ({ ...s, mock: true })),
    onProviders: (list) => {
      agentRef.current.providers = list;
      const bids = list.map((b) => ({
        name: b.name,
        phone: b.phone,
        rating: b.rating,
        mapsUrl: b.mapsUrl,
        quote: "",
      }));
      const existingId = jobIdRef.current;
      const title = agentRef.current.brief?.problem?.slice(0, 48) || "Service call";
      if (existingId && (houseRef.current.projects || []).some((p) => p.id === existingId)) {
        setHouse((h) => ({
          ...h,
          projects: (h.projects || []).map((p) =>
            p.id === existingId ? { ...p, status: "quoting", bids } : p
          ),
        }));
      } else {
        const id = uid();
        jobIdRef.current = id;
        setJobId(id);
        setHouse((h) => ({
          ...h,
          projects: [
            {
              id,
              title,
              kind: /renov|contractor/i.test(agentRef.current.brief?.trade || "")
                ? "reno"
                : "repair",
              status: "quoting",
              budget: agentRef.current.brief?.budget || "",
              notes: agentRef.current.brief?.problem || "",
              bids,
            },
            ...(h.projects || []),
          ],
        }));
      }
      if (!voiceLiveRef.current) setScreen("job");
    },
    onBrief: (line) => {
      agentRef.current.briefLine = line;
    },
    saveAsset: (asset) => {
      setHouse((h) => ({ ...h, assets: [...h.assets, asset] }));
    },
    patchAsset: (id, patch) => {
      setHouse((h) => ({
        ...h,
        assets: h.assets.map((a) => (a.id === id ? { ...a, ...patch } : a)),
      }));
    },
    captureFrame: () => captureFrame(videoRef.current),
    setCall,
    pollCall: (id, shop) => startPoll(id, shop),
  });

  const handleTurn = async (text, { speak } = {}) => {
    setBusy(true);
    try {
      const replies = await runTurn(text, toolCtx());
      replies.forEach((line) => addTranscript("HomeOps", line));
      if (speak && replies.length) {
        speakOps(replies.join(". "), {
          onStart: () => setVoiceState("speaking"),
          onEnd: () => {
            if (voiceLiveRef.current) setVoiceState("listening");
          },
        });
      }
      return replies;
    } catch (err) {
      addTranscript("HomeOps", err.message);
      if (speak) {
        speakOps(err.message, {
          onStart: () => setVoiceState("speaking"),
          onEnd: () => {
            if (voiceLiveRef.current) setVoiceState("listening");
          },
        });
      }
      return [];
    } finally {
      setBusy(false);
    }
  };

  const onVoiceTool = async (name, args) => {
    if (name === "find_local_pros") {
      const trade = args.trade || "handyman";
      const problem = args.problem || "";
      agentRef.current.brief = {
        address: houseRef.current.address,
        problem,
        trade,
        budget: args.budget,
        availability: args.availability,
        auto_book: true,
      };
      try {
        const data = await findProviders(trade, houseRef.current.address);
        if (data.mock) setApiState((s) => ({ ...s, mock: true }));
        toolCtx().onProviders(data.providers || []);
        const line = (data.providers || [])
          .map((p) => `${String(p.name).replace(/^\[MOCK\]\s*/i, "")}, ${p.rating}, ${p.phone}`)
          .join(". ");
        injectOpsContext(
          line
            ? `Shops found: ${line}. Call the top one now with call_shop — it books when the quote fits the budget.`
            : "No shops found. Ask for a different trade or address."
        );
      } catch (err) {
        injectOpsContext(`Could not find shops: ${err.message}`);
      }
      return;
    }
    if (name === "call_shop") {
      const label = args.name || args.phone;
      addTranscript("You", `Call ${label} for a quote.`);
      await handleTurn(`Call ${label} for a quote.`);
      return;
    }
    if (name === "save_item") {
      const room = pickRoom(houseRef.current, `${args.room || ""} ${args.category || ""}`);
      const id = uid();
      setHouse((h) => ({
        ...h,
        assets: [
          ...h.assets,
          {
            id,
            roomId: room?.id,
            category: args.category || "appliance",
            brand: args.brand || "",
            model: args.model || "",
            serial: args.serial || "",
            warrantyUntil: args.warranty || "",
          },
        ],
      }));
      injectOpsContext(`Saved ${args.brand || ""} ${args.model || args.category} in ${room?.name || "the house"}.`);
    }
  };

  const stopTalk = () => {
    voiceLiveRef.current = false;
    voiceModeRef.current = null;
    stopOpsVoice();
    setVoiceMode(null);
    setVoiceState("idle");
  };

  const startTalk = async () => {
    setScreen("chat");
    setVoiceError("");
    setVoiceState("connecting");
    voiceLiveRef.current = true;
    try {
      const snapshot = houseSnapshot(houseRef.current);
      const session = await mintVoiceSession(snapshot);
      if (session.mock) setApiState((s) => ({ ...s, mock: true }));
      const mode = await startOpsVoice({
        webrtcCode: session.webrtc_code,
        mode: session.mode,
        onState: (state) => {
          if (voiceLiveRef.current) setVoiceState(state);
        },
        onTranscript: (who, text) => {
          addTranscript(who, text);
          if (who === "You" && voiceModeRef.current === "browser") {
            handleTurn(text, { speak: true });
          }
        },
        onError: (msg) => setVoiceError(msg),
      });
      if (!voiceLiveRef.current) {
        stopOpsVoice();
        return;
      }
      voiceModeRef.current = mode;
      setVoiceMode(mode);
      if (mode === "browser") {
        addTranscript("HomeOps", session.first_message);
        speakOps(session.first_message, {
          onStart: () => setVoiceState("speaking"),
          onEnd: () => {
            if (voiceLiveRef.current) setVoiceState("listening");
          },
        });
      }
    } catch (err) {
      voiceLiveRef.current = false;
      setVoiceState("idle");
      setVoiceError(err.message);
    }
  };

  const sendChat = async () => {
    const text = chat.trim();
    if (!text || busy) return;
    addTranscript("You", text);
    setChat("");
    await handleTurn(text, { speak: voiceLiveRef.current && voiceModeRef.current === "browser" });
  };

  const goTab = (id) => {
    setItemId(null);
    setJobId(null);
    setIssueSeed("");
    if (id !== "chat") stopTalk();
    setScreen(id);
  };

  const askInChat = (q) => {
    goTab("chat");
    addTranscript("You", q);
    handleTurn(q);
  };

  const asset = house?.assets?.find((a) => a.id === itemId);
  const job = house?.projects?.find((p) => p.id === jobId);
  const chatLocked = screen === "chat";

  return (
    <IPhoneFrame>
      <div className="phone">
        <header className="status">
          <strong>HomeOps</strong>
          <span className="status-cluster">
            {apiState.mock ? (
              <span className="mock">Demo</span>
            ) : apiState.ok ? null : (
              <span className="mock">Offline</span>
            )}
          </span>
        </header>

      <main ref={stageRef} className={chatLocked ? "stage locked" : "stage"}>
        {screen === "home" && (
          <HomeScreen
            house={house}
            setScreen={goTab}
            openItem={(id) => {
              setItemId(id);
              setScreen("item");
            }}
            openJob={(id) => {
              setJobId(id);
              setScreen("job");
            }}
            startIssue={() => {
              setIssueSeed("");
              setScreen("issue");
            }}
            startJob={() => {
              setJobId(null);
              setScreen("job");
            }}
            onAddPhoto={() => photoRef.current?.click()}
            onAddress={(address) => setHouse((h) => ({ ...h, address }))}
            onAsk={askInChat}
          />
        )}
        {screen === "issue" && (
          <IssueScreen
            house={house}
            seed={issueSeed}
            onBack={() => setScreen("home")}
            onFind={(data) => {
              createIssueJob(data);
              const text = issueText(data, house);
              addTranscript("You", text);
              setScreen("chat");
              handleTurn(`${text}. Please find local providers.`);
            }}
            onChat={(data) => {
              createIssueJob(data);
              const text = issueText(data, house);
              addTranscript("You", text);
              setScreen("chat");
              handleTurn(text);
            }}
          />
        )}
        {screen === "inventory" && (
          <InventoryScreen
            house={house}
            fileError={fileError}
            onPhoto={onPhoto}
            openItem={(id) => {
              setItemId(id);
              setScreen("item");
            }}
            setScreen={goTab}
            onAddRoom={(name) =>
              setHouse((h) => ({ ...h, rooms: [...h.rooms, { id: uid(), name }] }))
            }
          />
        )}
        {screen === "item" && (
          <ItemScreen
            house={house}
            asset={asset}
            onBack={() => {
              setItemId(null);
              setScreen("inventory");
            }}
            onChange={(next) => {
              setHouse((h) => ({
                ...h,
                assets: h.assets.map((a) => (a.id === next.id ? next : a)),
              }));
            }}
            onDelete={(id) => {
              setHouse((h) => ({ ...h, assets: h.assets.filter((a) => a.id !== id) }));
              setItemId(null);
              setScreen("inventory");
            }}
            askAbout={(a) => {
              const q = `Tell me about the ${a.brand || ""} ${a.model || a.category}`.trim();
              askInChat(q);
            }}
            onBroke={(a) => {
              setIssueSeed(`The ${a.brand || ""} ${a.model || a.category} isn’t working`.trim());
              setScreen("issue");
            }}
          />
        )}
        {screen === "projects" && (
          <ProjectsScreen
            house={house}
            openJob={(id) => {
              setJobId(id);
              setScreen("job");
            }}
            startJob={() => {
              setJobId(null);
              setScreen("job");
            }}
          />
        )}
        {screen === "job" && (
          <JobScreen
            house={house}
            job={job}
            call={call}
            busy={busy}
            onBack={() => {
              setJobId(null);
              setScreen("projects");
            }}
            onChange={(data, isNew) => {
              if (isNew) {
                const id = uid();
                setHouse((h) => ({
                  ...h,
                  projects: [{ id, ...data }, ...(h.projects || [])],
                }));
                setJobId(id);
              } else {
                patchProject(data.id, () => data);
              }
            }}
            onCall={(shop) => {
              jobIdRef.current = job.id;
              agentRef.current.providers = job.bids || [];
              agentRef.current.brief = {
                address: house.address,
                problem: job.title,
                trade: job.kind === "reno" ? "contractor" : "plumber",
                budget: job.budget,
                auto_book: true,
              };
              addTranscript("You", `Call ${shop.name}.`);
              handleTurn(`Call ${shop.name} for a quote.`);
            }}
            onFindPros={(j) => {
              setJobId(j.id);
              jobIdRef.current = j.id;
              const room = j.roomId ? roomLabel(house, j.roomId) : "";
              const text = `${j.title}. ${j.notes || ""} ${j.budget ? `Budget ${j.budget}` : ""} ${room}`.trim();
              addTranscript("You", `Find pros for ${j.title}`);
              handleTurn(`${text}. Please find local providers.`);
            }}
            onDelete={(id) => {
              setHouse((h) => ({
                ...h,
                projects: (h.projects || []).filter((p) => p.id !== id),
              }));
              setJobId(null);
              setScreen("projects");
            }}
          />
        )}
        {screen === "chat" && (
          <ChatScreen
            live={live}
            videoRef={videoRef}
            mediaError={mediaError}
            chat={chat}
            setChat={setChat}
            sendChat={sendChat}
            startLive={startLive}
            stopLive={stopLive}
            transcript={transcript}
            busy={busy}
            voiceState={voiceState}
            voiceMode={voiceMode}
            voiceError={voiceError}
            onTalk={startTalk}
            onHangup={stopTalk}
            onSuggest={(text) => {
              addTranscript("You", text);
              handleTurn(text, { speak: voiceLiveRef.current && voiceModeRef.current === "browser" });
            }}
          />
        )}
      </main>

      <input
        ref={photoRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={onPhoto}
        hidden
      />

      <nav className="dock">
        {NAV.slice(0, 2).map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={
              screen === tab.id ||
              (tab.id === "home" && screen === "issue") ||
              (tab.id === "inventory" && screen === "item")
                ? "on"
                : ""
            }
            onClick={() => goTab(tab.id)}
          >
            <Icon name={tab.icon} />
            {tab.label}
          </button>
        ))}
        <button
          type="button"
          className={`talk-fab${
            voiceState === "listening" || voiceState === "speaking" || voiceState === "connecting"
              ? " live"
              : ""
          }${voiceState === "speaking" ? " speaking" : ""}`}
          onClick={startTalk}
          aria-label="Talk to Ops"
        >
          <Icon name="mic" size={26} />
        </button>
        {NAV.slice(2).map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={
              screen === tab.id || (tab.id === "projects" && screen === "job") ? "on" : ""
            }
            onClick={() => goTab(tab.id)}
          >
            <Icon name={tab.icon} />
            {tab.label}
          </button>
        ))}
      </nav>

      {liveCall ? (
        <CallOverlay call={liveCall} turns={callTurns} onClose={closeCallOverlay} />
      ) : null}
      </div>
    </IPhoneFrame>
  );
}
