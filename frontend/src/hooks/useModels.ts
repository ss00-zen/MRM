import { useQuery } from "@tanstack/react-query";
import api from "../services/api";

export const useModels = () => {
  return useQuery({
    queryKey: ["models"],
    queryFn: async () => {
      const res = await api.get("/models");
      return res.data;
    },
  });
};
