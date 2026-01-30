
import { Card, CardBody, CardHeader } from "../../../ui/Card";
import { Button } from "../../../ui/Button";

export type ProxySummary = {
  id: string;
  name: string;
  status: "running" | "stopped" | "error" | string;
};

export function ProxyCard({
  proxy,
  onOpenDetails,
  onOpenActions,
}: {
  proxy: ProxySummary;
  onOpenDetails: () => void;
  onOpenActions: () => void;
}) {
  return (
    <Card className="cursor-pointer" >
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="truncate font-medium">{proxy.name}</div>
            <div className="text-xs text-muted-foreground">ID: {proxy.id}</div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">{proxy.status}</span>
            <Button variant="ghost" size="sm" onClick={(e) => { e.preventDefault(); e.stopPropagation(); onOpenActions(); }}>
              Actions
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        <button className="text-sm underline underline-offset-4" onClick={(e) => { e.preventDefault(); e.stopPropagation(); onOpenDetails(); }}>
          Open details
        </button>
      </CardBody>
    </Card>
  );
}
