import { drawingNotes, knownAssetLine, pickRoom, uid } from "./house.js";
import { findProviders, getCall, lookupModel, placeCall } from "./api.js";

const DANGER =
  /\b(gas\s+leak|smell(?:s|ing)?\s+gas|carbon\s+monoxide|\bfire\b|flames|uncontrolled\s+flood|(?:can(?:not|'t| not))\s+stop\s+(?:the\s+)?(?:water|flood|leak))\b/i;

const STOP = /\b(stop(?: calling| outreach)?|don't call|do not call|cancel (?:the )?calls?)\b/i;

const WANT_CALL =
  /\b(call (?:them|him|her|the|a |it)|go ahead|yes,? call|handle it|please call|place the call|call for (?:a )?quote)\b/i;

const WANT_NEXT = /\b(try (?:the )?next|call (?:the )?next|another (?:shop|one|provider))\b/i;

const WANT_FIND =
  /\b(find (?:me )?(?:local |a |some )?(?:providers?|pros?|shops?|someone|help)|get (?:me )?(?:a )?(?:quote|pro))\b/i;

export function isDanger(text) {
  return DANGER.test(text);
}

export function inferTrade(text) {
  if (/plumb|leak|pipe|drain|toilet|water heater|supply line/i.test(text)) return "plumber";
  if (/fridge|refrigerat|dishwasher|washer|dryer|oven|appliance|ice.?maker/i.test(text)) {
    return "appliance repair";
  }
  if (/renovat|remodel|contractor/i.test(text)) return "contractor";
  if (/hvac|furnace|ac |air cond/i.test(text)) return "hvac";
  return "handyman";
}

export function parseBudget(text) {
  const match = text.match(/\$\s?(\d{2,6})|\bbudget\s*(?:of\s*|is\s*)?\$?\s*(\d{2,6})/i);
  if (!match) return null;
  const n = match[1] || match[2];
  return `$${n}`;
}

export function parseAvailability(text) {
  const match = text.match(
    /\b(after\s+\d{1,2}(?:\s*(?:am|pm))?|tomorrow|weekend|evenings?|weekdays?|this week|next week|mornings?)\b/i
  );
  return match ? match[0] : null;
}

export function homeownerFromHouse(house) {
  const hit = (house?.details || []).find((d) =>
    /^(homeowner|owner|resident)$/i.test(String(d.label || "").trim())
  );
  return String(hit?.value || "").trim();
}

export function parseAppliance(text) {
  const categoryMatch = text.match(
    /\b(fridge|refrigerator|dishwasher|washer|dryer|oven|stove|range|furnace|hvac|water heater)\b/i
  );
  const category = categoryMatch
    ? /fridge|refrigerat/i.test(categoryMatch[0])
      ? "fridge"
      : categoryMatch[0].toLowerCase()
    : "appliance";
  const branded = text.match(
    /\b(GE|Whirlpool|Samsung|LG|Bosch|KitchenAid|Maytag|Frigidaire|Kenmore|Sub-Zero|Wolf)\b/i
  );
  const model = text.match(
    /\b([A-Z]{1,4}\d{2,}[A-Z0-9-]{0,8}|\d{2,}[A-Z]{2,}\d*)\b/
  );
  const brand = branded ? branded[1] : null;
  const modelId = model ? model[1] : null;
  const confident = Boolean(brand && modelId);
  return { category, brand, model: modelId, confident };
}

function looksLikeInventory(text) {
  return (
    /\b(this is (?:the |our |my )?(fridge|refrigerator|dishwasher|washer|dryer|oven|stove)|data plate|model (?:is|number)|it's a |its a )\b/i.test(
      text
    ) || parseAppliance(text).confident
  );
}

function looksLikeProblem(text) {
  return /\b(leak|leaking|broken|broke|not working|doesn't work|does not work|renovate|remodel|repair|fix|flooding|(?:won'?t|isn'?t|not|stopped) (?:cool|cooling|start|starting|drain|draining|heat|heating|work|working|run|running)|acting up)\b/i.test(
    text
  );
}

function namedProvider(text, providers) {
  const lower = text.toLowerCase();
  return providers.find((p) => lower.includes(String(p.name).toLowerCase().replace(/^\[mock\]\s*/i, "")));
}

function answerFromHome(text, house) {
  const lower = text.toLowerCase();
  if (!/what|which|when|where|who|warranty|model|serial|paint|plumber|manual|how old/i.test(lower)) {
    return null;
  }
  const hit = house.assets.find((a) => {
    const blob = `${a.category} ${a.brand} ${a.model}`.toLowerCase();
    if (/fridge|refrigerat/.test(lower) && /fridge|refrigerat/.test(blob)) return true;
    if (/dishwasher/.test(lower) && /dishwasher/.test(blob)) return true;
    if (/washer(?! water)/.test(lower) && /washer/.test(blob)) return true;
    if (/oven|stove|range/.test(lower) && /oven|stove|range/.test(blob)) return true;
    if (/faucet|kohler/.test(lower) && /faucet|kohler/.test(blob)) return true;
    return false;
  });
  if (hit) {
    return [
      `${hit.brand || ""} ${hit.model || hit.category}`.trim(),
      hit.serial && `serial ${hit.serial}`,
      hit.warrantyUntil && `warranty through ${hit.warrantyUntil}`,
      hit.purchased && `bought ${hit.purchased}`,
      hit.exaSummary,
    ]
      .filter(Boolean)
      .join(". ");
  }
  const detail = (house.details || []).find(
    (d) => /paint/.test(lower) || lower.includes(d.label.toLowerCase().split(" ")[0])
  );
  if (detail && /paint/.test(lower)) {
    return `${detail.label}: ${detail.value}`;
  }
  const pro = (house.contractors || [])[0];
  if (pro && /plumb|who did|contractor/.test(lower)) {
    return `${pro.name}, ${pro.trade}. ${pro.phone}. Last: ${pro.lastJob || "on file"}.`;
  }
  return null;
}

export async function runTurn(text, ctx) {
  const say = [];
  const agent = ctx.agent;

  const homeAnswer = answerFromHome(text, ctx.house);
  if (homeAnswer && !looksLikeProblem(text) && !looksLikeInventory(text)) {
    ctx.onActivity("home_record · answered from inventory");
    say.push(homeAnswer);
    return say;
  }

  if (isDanger(text)) {
    agent.stopped = true;
    ctx.onActivity("blocked · danger — no vendor call");
    say.push(
      "That sounds like an emergency. Call emergency services now. HomeOps will not call a vendor for gas, fire, or a flood you cannot stop."
    );
    return say;
  }

  if (STOP.test(text)) {
    agent.stopped = true;
    ctx.onActivity("outreach · stopped");
    say.push("Stopping outreach. I will not start further calls.");
    return say;
  }

  if (looksLikeInventory(text)) {
    const parsed = parseAppliance(text);
    if (!parsed.confident) {
      say.push(
        "I can tell it's an appliance, but I'm not confident on the brand and model. Show me the data plate or tell me both."
      );
      return say;
    }
    const room = pickRoom(ctx.house, text);
    const asset = {
      id: uid(),
      roomId: room.id,
      category: parsed.category,
      brand: parsed.brand,
      model: parsed.model,
      photoDataUrl: ctx.captureFrame?.(),
    };
    ctx.saveAsset(asset);
    ctx.onActivity(`save_asset · ${room.name} ${parsed.brand} ${parsed.model}`);
    say.push(`Saved ${parsed.brand} ${parsed.model} to ${room.name}. I'll look that up.`);
    try {
      const query = `${parsed.brand} ${parsed.model} ${parsed.category} manual specs parts`;
      const exa = await lookupModel(query);
      if (exa.mock) ctx.onMock(true);
      ctx.patchAsset(asset.id, { exaSummary: exa.summary, exaUrl: exa.url });
      ctx.onActivity(
        exa.mock ? `lookup_model · [MOCK] ${parsed.brand} ${parsed.model}` : `lookup_model · ${parsed.brand} ${parsed.model}`
      );
      say.push(
        exa.mock
          ? `[MOCK] Lookup: ${exa.summary}`
          : `Lookup: ${exa.summary}${exa.url ? ` (${exa.url})` : ""}`
      );
    } catch (err) {
      ctx.onActivity(`lookup_model · failed: ${err.message}`);
      say.push("I saved the visual ID. The model lookup did not come back.");
    }
    return say;
  }

  if (WANT_NEXT.test(text) || WANT_CALL.test(text) || namedProvider(text, agent.providers)) {
    if (agent.stopped) {
      say.push("Outreach is stopped. Say you want to resume if you change your mind.");
      return say;
    }
    if (!agent.providers.length) {
      if (agent.brief) {
        const more = await searchProviders(agent.brief, ctx, say);
        if (!more) return say;
      } else {
        say.push("I don't have shops yet. Tell me what broke and I'll find local providers.");
        return say;
      }
    }
    const tryAnother = WANT_NEXT.test(text) || agent.callCount >= 3;
    await callShop(text, ctx, say, tryAnother);
    return say;
  }

  if (looksLikeProblem(text) || WANT_FIND.test(text) || agent.pendingBrief) {
    const source = agent.pendingBrief
      ? {
          ...agent.pendingBrief,
          budget: agent.pendingBrief.budget || parseBudget(text),
          availability: agent.pendingBrief.availability || parseAvailability(text),
          problem: agent.pendingBrief.problem || text,
        }
      : buildBrief(text, ctx.house);
    const missing = !source.budget || !source.availability;
    if (missing && !agent.askedOnce && !agent.pendingBrief) {
      agent.askedOnce = true;
      agent.pendingBrief = source;
      ctx.onBrief(formatBrief(source));
      say.push("Got it. Any budget or time window I should mention, or should I proceed without them?");
      return say;
    }
    agent.pendingBrief = null;
    agent.brief = source;
    ctx.onBrief(formatBrief(source));
    const found = await searchProviders(source, ctx, say);
    if (!found) return say;
    await callShop(text, ctx, say, false);
    return say;
  }

  say.push(
    "Ask me anything about this house, snap an appliance, or tell me what broke. I'll find local pros, call for quotes, and book the first one that fits your budget."
  );
  return say;
}

function buildBrief(text, house) {
  const trade = inferTrade(text);
  const reno = /renovat|remodel/i.test(text);
  const problem = text
    .replace(/\.?\s*Please find local providers\.?\s*$/i, "")
    .trim();
  return {
    address: house.address,
    homeowner: homeownerFromHouse(house),
    problem,
    trade,
    budget: parseBudget(text),
    availability: parseAvailability(text),
    asset: knownAssetLine(house, text) || null,
    drawings_note: reno || /bath/i.test(text) ? drawingNotes(house, text) || null : null,
    auto_book: true,
  };
}

function formatBrief(brief) {
  return [
    brief.problem,
    brief.trade,
    brief.budget && `budget ${brief.budget}`,
    brief.availability,
    brief.drawings_note && `drawing ${brief.drawings_note} on file`,
    brief.asset && `inventory ${brief.asset}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

async function searchProviders(brief, ctx, say) {
  const agent = ctx.agent;
  if (!brief.address) {
    say.push("I need a house address first (House screen). I will not place a call without it.");
    ctx.onActivity("find_providers · blocked: no address");
    return false;
  }
  ctx.onActivity(`find_providers · ${brief.trade} near ${brief.address}`);
  try {
    const data = await findProviders(brief.trade, brief.address);
    if (data.mock) ctx.onMock(true);
    const providers = data.providers || [];
    agent.providers = providers;
    ctx.onProviders(providers);
    if (!providers.length) {
      ctx.onActivity("find_providers · none callable");
      say.push("I couldn't find a callable shop nearby. I will not place a call.");
      return false;
    }
    const top = providers[0];
    const label = data.mock ? "[MOCK] " : "";
    say.push(
      `${label}${providers.length} shop${providers.length === 1 ? "" : "s"}, preferring higher ratings. Top: ${top.name} ${top.rating}. I'll call down the list and book the first that fits your budget.`
    );
    return true;
  } catch (err) {
    ctx.onActivity(`find_providers · failed: ${err.message}`);
    say.push(`Provider search failed: ${err.message}`);
    return false;
  }
}

async function callShop(text, ctx, say, tryAnother) {
  const agent = ctx.agent;
  if (agent.stopped) {
    say.push("Outreach is stopped.");
    return;
  }
  if (agent.callCount >= 3 && !tryAnother) {
    say.push("I've already called 3 providers. Say try another if you want one more.");
    return;
  }
  const called = agent.calledPhones || new Set();
  const named = namedProvider(text, agent.providers);
  const shop =
    named || agent.providers.find((p) => !called.has(p.phone)) || agent.providers[0];
  if (!shop?.phone) {
    say.push("No callable number on file.");
    return;
  }
  const brief = agent.brief || {
    address: ctx.house.address,
    homeowner: homeownerFromHouse(ctx.house),
    problem: text,
    trade: inferTrade(text),
    auto_book: true,
  };
  ctx.setCall(`Dialing ${shop.name}…`);
  ctx.onActivity(
    `call_provider · ${shop.name}${tryAnother ? " (try another)" : ""}`
  );
  try {
    const started = await placeCall(shop.phone, brief, tryAnother, shop.name);
    if (started.mock) ctx.onMock(true);
    agent.callCount += 1;
    called.add(shop.phone);
    agent.calledPhones = called;
    agent.lastCallId = started.call_id;
    ctx.pollCall(started.call_id, shop);
    say.push(
      started.mock
        ? `[MOCK] Calling ${shop.name}. If the quote fits your budget, I'll book them.`
        : `Calling ${shop.name}. If the quote fits your budget, I'll book them.`
    );
  } catch (err) {
    ctx.setCall(`Call failed: ${err.message}`);
    ctx.onActivity(`call_provider · failed: ${err.message}`);
    say.push(`The call did not go through: ${err.message}. I can try the next shop.`);
  }
}

export function watchCall(callId, { onState, onDone, onError }) {
  let ticks = 0;
  const timer = window.setInterval(async () => {
    ticks += 1;
    try {
      const data = await getCall(callId);
      onState(data);
      if (data.state === "done" || data.state === "failed" || ticks > 90) {
        window.clearInterval(timer);
        onDone(data);
      }
    } catch (err) {
      window.clearInterval(timer);
      onError(err);
    }
  }, 800);
  return () => window.clearInterval(timer);
}

export { formatBrief, buildBrief };
