-- USE_THIS_title_chr_live_tile_probe.lua
-- Mesen 0.9.9 classic Lua.
--
-- Purpose:
--   Dump the real PPU nametable/CHR tile usage visible on the title screen.
--   This is for checking whether bank-in-CHR tiles $1DE/$1DF are actually
--   used by the live emulator state, and what tiles form the orange floor band.
--
-- Usage:
--   1. Load the normalized ROM in Mesen.
--   2. Stop on the title screen.
--   3. Run this script.
--   4. Wait about 1 second.
--   5. Send mesen_probes/logs/title_chr_live_tile_probe_log.txt to Codex.

local LOG = "D:\\chaos\\MAGATU_EMULATOR\\SOLOMON_CUSTOMIZER\\mesen_probes\\logs\\title_chr_live_tile_probe_log.txt"
local fh = io.open(LOG, "w")

local function w(s)
  if fh then fh:write(s .. "\n"); fh:flush() end
  emu.log(s)
end

if not fh then
  emu.log("!! io.open failed: " .. LOG)
end

local PPU = emu.memType.ppuDebug
local CPU = emu.memType.cpuDebug
local frame = 0
local dumped = false

local function rppu(a)
  local ok, v = pcall(emu.read, a, PPU)
  if ok and v ~= nil then return v end
  return 0
end

local function rcpu(a)
  local ok, v = pcall(emu.read, a, CPU)
  if ok and v ~= nil then return v end
  return 0
end

local function hx(v, n)
  if n == 2 then return string.format("%02X", v & 0xFF) end
  return string.format("%03X", v & 0xFFF)
end

local function bg_pattern_base()
  local ppuctrl = rcpu(0x0300)
  if (math.floor(ppuctrl / 0x10) % 2) ~= 0 then
    return 0x1000
  end
  return 0x0000
end

local function chr_bank_tile_for_nt_tile(nt_tile)
  -- Title uses BG pattern table. If bg_pattern_base=$1000, tile $DE means
  -- bank-in-CHR tile $1DE. If $0000, it means $0DE.
  return math.floor(bg_pattern_base() / 16) + (nt_tile & 0xFF)
end

local function dump_nt_rows(nt_base, label)
  w(string.format("NAMETABLE %s $%04X rows 00-29 raw tile values:", label, nt_base))
  for row = 0, 29 do
    local t = {}
    for col = 0, 31 do
      t[#t + 1] = string.format("%02X", rppu(nt_base + row * 32 + col))
    end
    w(string.format("%s row %02d: %s", label, row, table.concat(t, " ")))
  end
end

local function dump_targets(nt_base, label, targets)
  w(string.format("TARGET SEARCH %s $%04X", label, nt_base))
  local counts = {}
  for _, bt in ipairs(targets) do counts[bt] = 0 end
  for row = 0, 29 do
    for col = 0, 31 do
      local tile = rppu(nt_base + row * 32 + col)
      local bt = chr_bank_tile_for_nt_tile(tile)
      if counts[bt] ~= nil then
        counts[bt] = counts[bt] + 1
        w(string.format(
          "HIT %s bankTile=$%03X ntTile=$%02X row=%02d col=%02d ppu=$%04X",
          label, bt, tile, row, col, nt_base + row * 32 + col))
      end
    end
  end
  for _, bt in ipairs(targets) do
    w(string.format("COUNT %s bankTile=$%03X count=%d", label, bt, counts[bt]))
  end
end

local function dump_rows_unique(nt_base, label, row_first, row_last)
  w(string.format("ROW UNIQUE %s rows %02d-%02d as bank-in-CHR tiles", label, row_first, row_last))
  for row = row_first, row_last do
    local seen = {}
    local list = {}
    for col = 0, 31 do
      local tile = rppu(nt_base + row * 32 + col)
      local bt = chr_bank_tile_for_nt_tile(tile)
      if not seen[bt] then
        seen[bt] = true
        list[#list + 1] = bt
      end
    end
    table.sort(list)
    local out = {}
    for _, bt in ipairs(list) do out[#out + 1] = "$" .. hx(bt, 3) end
    w(string.format("%s row %02d unique: %s", label, row, table.concat(out, " ")))
  end
end

local function dump_chr_patterns(targets)
  w("CHR PATTERNS for targets, PPU debug memory")
  for _, bt in ipairs(targets) do
    local base = bt * 16
    local t = {}
    for i = 0, 15 do t[#t + 1] = string.format("%02X", rppu(base + i)) end
    w(string.format("CHR bankTile=$%03X ppu=$%04X bytes: %s", bt, base, table.concat(t, " ")))
  end
end

local function dump()
  dumped = true
  local targets = {0x1DE, 0x1DF, 0x124}
  w("=== title_chr_live_tile_probe ===")
  w("frame=" .. tostring(frame))
  w(string.format("CPU $0300=%02X bg_pattern_base=$%04X", rcpu(0x0300), bg_pattern_base()))
  w("NOTE: bankTile = bg_pattern_base/16 + nametable tile value")
  dump_targets(0x2000, "NT2000", targets)
  dump_targets(0x2800, "NT2800", targets)
  dump_rows_unique(0x2000, "NT2000", 24, 29)
  dump_rows_unique(0x2800, "NT2800", 24, 29)
  dump_chr_patterns(targets)
  dump_nt_rows(0x2000, "NT2000")
  dump_nt_rows(0x2800, "NT2800")
  w("=== end title_chr_live_tile_probe ===")
  emu.displayMessage("probe", "title chr live tile dump done")
end

emu.addEventCallback(function()
  frame = frame + 1
  if (not dumped) and frame >= 60 then
    dump()
  end
end, emu.eventType.endFrame)

emu.log("USE_THIS_title_chr_live_tile_probe loaded. Wait on title screen for 1 second.")
