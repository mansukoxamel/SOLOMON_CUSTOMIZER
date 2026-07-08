-- bullet91_wallpass_probe.lua
-- Mesen 0.9.9 classic Lua probe.
--
-- Purpose:
--   Trace custom enemy $8B (Bullet91) after the wall-pass runtime change.
--   It records main-slot/sub-slot values, behavior state, velocity, position,
--   distance-to-Dana fields, and any unexpected entry into the stock Bullet
--   wall collision path.
--
-- Output:
--   D:\chaos\MAGATU_EMULATOR\SOLOMON_CUSTOMIZER\mesen_probes\logs\bullet91_wallpass_probe_log.txt

local LOG = "D:\\chaos\\MAGATU_EMULATOR\\SOLOMON_CUSTOMIZER\\mesen_probes\\logs\\bullet91_wallpass_probe_log.txt"
local fh = io.open(LOG, "w")

local function log(s)
  if fh then
    fh:write(s .. "\n")
    fh:flush()
  end
  emu.log(s)
end

local function R(a)
  return emu.read(a & 0xFFFF, emu.memType.cpuDebug)
end

local function PTR(lo)
  return R(lo) + 256 * R(lo + 1)
end

local function sx(v)
  if v >= 0x80 then return v - 0x100 end
  return v
end

local function frame_pc()
  local st = emu.getState()
  local frame = 0
  local pc = 0
  local a = 0
  local x = 0
  local y = 0
  if st and st.ppu then frame = st.ppu.frameCount or 0 end
  if st and st.cpu then
    pc = st.cpu.pc & 0xFFFF
    a = st.cpu.a & 0xFF
    x = st.cpu.x & 0xFF
    y = st.cpu.y & 0xFF
  end
  return frame, pc, a, x, y
end

local function main_ptr_for_slot(slot)
  return 0x057F + (slot * 0x14)
end

local function sub_ptr_for_slot(slot)
  return 0x04F7 + (slot * 0x08)
end

local function main_line(ptr)
  return string.format(
    "main=$%04X st=$%02X type=$%02X beh=$%02X state=%d dir=%d y=$%02X x=$%02X yv=$%02X(%+d) xv=$%02X(%+d)",
    ptr,
    R(ptr + 0), R(ptr + 1), R(ptr + 3), (R(ptr + 3) >> 2) & 0x3F, R(ptr + 3) & 0x03,
    R(ptr + 7), R(ptr + 10), R(ptr + 5), sx(R(ptr + 5)), R(ptr + 8), sx(R(ptr + 8))
  )
end

local function sub_line(ptr)
  return string.format(
    "sub=$%04X s0=$%02X s1=$%02X s2=$%02X s3=$%02X dy2=$%02X(%+d) dx2=$%02X(%+d) s6=$%02X s7=$%02X",
    ptr,
    R(ptr + 0), R(ptr + 1), R(ptr + 2), R(ptr + 3),
    R(ptr + 4), sx(R(ptr + 4)), R(ptr + 5), sx(R(ptr + 5)), R(ptr + 6), R(ptr + 7)
  )
end

local count = 0
local LIMIT = 3000
local last_sig = {}

local function trace(tag, msg)
  if count >= LIMIT then return end
  count = count + 1
  local frame, pc, a, x, y = frame_pc()
  log(string.format("%06d,%04d,%s,pc=$%04X,A=$%02X,X=$%02X,Y=$%02X,%s", frame, count, tag, pc, a, x, y, msg or ""))
end

local function current_lines()
  local sub = PTR(0x2C)
  local main = PTR(0x2E)
  return sub_line(sub) .. "," .. main_line(main)
end

local function current_is_8b()
  local main = PTR(0x2E)
  return R(main + 1) == 0x8B
end

log("frame,n,tag,pc,A,X,Y,details")
log("=== bullet91_wallpass_probe start ===")
log("sub-slot common: s0=status, s1=state timer, s4=dy/2, s5=dx/2, s6/s7=child or type-specific work")

emu.addEventCallback(function()
  for slot = 0, 16 do
    local main = main_ptr_for_slot(slot)
    if R(main + 1) == 0x8B then
      local sub = sub_ptr_for_slot(slot)
      local sig = string.format(
        "%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X",
        R(main + 0), R(main + 3), R(main + 5), R(main + 7), R(main + 8), R(main + 10),
        R(sub + 0), R(sub + 1), R(sub + 2), R(sub + 3), R(sub + 4), R(sub + 5), R(sub + 6), R(sub + 7)
      )
      if last_sig[slot] ~= sig then
        last_sig[slot] = sig
        trace("SCAN_SLOT_" .. slot, sub_line(sub) .. "," .. main_line(main))
      end
    end
  end
end, emu.eventType.endFrame)

emu.addMemoryCallback(function()
  if current_is_8b() then trace("BULLET91_AI_EF57", current_lines()) end
end, emu.memCallbackType.cpuExec, 0xEF57)

emu.addMemoryCallback(function()
  if current_is_8b() then trace("STOCK_STATE0_AFC7", current_lines()) end
end, emu.memCallbackType.cpuExec, 0xAFC7)

emu.addMemoryCallback(function()
  if current_is_8b() then trace("STOCK_STATE1_B00A", current_lines()) end
end, emu.memCallbackType.cpuExec, 0xB00A)

emu.addMemoryCallback(function()
  if current_is_8b() then trace("UNEXPECTED_STOCK_WALL_AFD8", current_lines()) end
end, emu.memCallbackType.cpuExec, 0xAFD8)

emu.addMemoryCallback(function()
  if current_is_8b() then trace("UNEXPECTED_WALL_MASK_AC39", current_lines()) end
end, emu.memCallbackType.cpuExec, 0xAC39)

emu.addMemoryCallback(function()
  if current_is_8b() then trace("DESPAWN_B376", current_lines()) end
end, emu.memCallbackType.cpuExec, 0xB376)

emu.log("bullet91_wallpass_probe loaded. 操作後、logs\\bullet91_wallpass_probe_log.txt を送ってください。")
