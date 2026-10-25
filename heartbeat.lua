-- 0x Rejoin heartbeat  (put this in your executor's autoexec folder)
-- Writes hb_<name>.txt to the executor workspace every few seconds.
-- The Python tool reads it: stale file = crash / stuck lobby, "disconnect" = kicked.

local HB_ID    = nil   -- leave nil to use your Roblox username as the name
local INTERVAL = 5     -- seconds between heartbeats

local Players    = game:GetService("Players")
local GuiService = game:GetService("GuiService")

if not game:IsLoaded() then game.Loaded:Wait() end
repeat task.wait() until Players.LocalPlayer

local id   = HB_ID or Players.LocalPlayer.Name
local FILE = "hb_" .. id .. ".txt"
local disconnected = false

local function write(status)
    pcall(function()
        writefile(FILE, os.time() .. "|" .. game.PlaceId .. "|" .. status)
    end)
end

local function markDisconnected()
    disconnected = true
    write("disconnect")
end

-- Kick / disconnect detection (two methods, either one is enough)
pcall(function()
    GuiService.ErrorMessageChanged:Connect(function(msg)
        if msg and msg ~= "" then markDisconnected() end
    end)
end)
task.spawn(function()
    pcall(function()
        local overlay = game:GetService("CoreGui")
            :WaitForChild("RobloxPromptGui", 15)
            :WaitForChild("promptOverlay", 15)
        overlay.ChildAdded:Connect(function(child)
            if child.Name == "ErrorPrompt" then markDisconnected() end
        end)
    end)
end)

-- Heartbeat loop
task.spawn(function()
    while true do
        write(disconnected and "disconnect" or "alive")
        task.wait(INTERVAL)
    end
end)
