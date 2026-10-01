import { toast } from "sonner";

export const notify = {
  success: (msg: string) => toast.success(msg, { duration: 3000 }),
  info: (msg: string) => toast.info(msg),
  warning: (msg: string) => toast.warning(msg, { duration: 6000 }),
  error: (msg: string) => toast.error(msg, { duration: 8000 }),
};
