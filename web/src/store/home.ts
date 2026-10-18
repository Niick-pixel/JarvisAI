// Home Assistant state for the Home sheet: the connection, the devices, and taps in flight.
import { create } from "zustand";
import { homeApi } from "../api/home";
import type { Device, HomeAction, HomeStatus } from "../api/types";
import { toast } from "./toast";

interface HomeState {
  status: HomeStatus | null;
  devices: Device[];
  error: string;
  pending: Record<string, boolean>;
  refresh: () => Promise<void>;
  loadDevices: () => Promise<void>;
  connect: (url: string, token: string) => Promise<boolean>;
  disconnect: () => Promise<void>;
  setRouteChat: (on: boolean) => Promise<void>;
  act: (device: Device, action: HomeAction, value?: number) => Promise<void>;
  say: (text: string) => Promise<string>;
}

const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

export const useHome = create<HomeState>((set, get) => ({
  status: null,
  devices: [],
  error: "",
  pending: {},
  refresh: async () => {
    const status = await homeApi.status();
    set({ status });
    if (status.connected) await get().loadDevices();
  },
  loadDevices: async () => {
    try {
      set({ devices: await homeApi.devices(), error: "" });
    } catch (error) {
      set({ error: message(error) });
    }
  },
  connect: async (url, token) => {
    try {
      set({ status: await homeApi.connect(url, token), error: "" });
      await get().loadDevices();
      return true;
    } catch (error) {
      set({ error: message(error) });
      return false;
    }
  },
  disconnect: async () => {
    set({ status: await homeApi.disconnect(), devices: [] });
  },
  setRouteChat: async (on) => {
    set({ status: await homeApi.setRouteChat(on) });
  },
  act: async (device, action, value) => {
    set((s) => ({ pending: { ...s.pending, [device.entity_id]: true } }));
    try {
      set({ devices: await homeApi.act(device.entity_id, action, value) });
    } catch (error) {
      toast(`${device.name}: ${message(error)}`, "error");
    } finally {
      set((s) => ({ pending: { ...s.pending, [device.entity_id]: false } }));
    }
  },
  say: async (text) => {
    const result = await homeApi.assist(text);
    if (result.handled) void get().loadDevices();
    return result.handled ? result.reply : "Home Assistant didn't recognise that as a home command.";
  },
}));
