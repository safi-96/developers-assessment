import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Eye, Wallet } from "lucide-react"
import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"

const pageSize = 10

export const Route = createFileRoute("/_layout/worklogs")({
  component: WorklogsPage,
  head: () => ({
    meta: [
      {
        title: "Worklogs - FastAPI Cloud",
      },
    ],
  }),
})

function WorklogsPage() {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [periodStart, setPeriodStart] = useState("2026-03-01")
  const [periodEnd, setPeriodEnd] = useState("2026-03-31")
  const [remittanceStatus, setRemittanceStatus] = useState("ALL")
  const [page, setPage] = useState(1)
  const [excludedWorklogIds, setExcludedWorklogIds] = useState<string[]>([])
  const [excludedFreelancerIds, setExcludedFreelancerIds] = useState<string[]>([])
  const [activeWorklogId, setActiveWorklogId] = useState<string | null>(null)

  const apiBase = `${import.meta.env.VITE_API_URL}/api/v1`

  const {
    data: listData,
    isLoading: isListLoading,
    isError: isListError,
  } = useQuery<any>({
    queryKey: ["worklogs", periodStart, periodEnd, remittanceStatus],
    queryFn: async () => {
      const token = localStorage.getItem("access_token") || ""
      const params = new URLSearchParams()
      if (periodStart) params.set("periodStart", periodStart)
      if (periodEnd) params.set("periodEnd", periodEnd)
      if (remittanceStatus !== "ALL") params.set("remittanceStatus", remittanceStatus)

      const res = await fetch(`${apiBase}/list-all-worklogs?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        throw new Error("Failed to load worklogs")
      }
      return res.json()
    },
  })

  const {
    data: detailData,
    isLoading: isDetailLoading,
    isError: isDetailError,
  } = useQuery<any>({
    queryKey: ["worklog-detail", activeWorklogId],
    enabled: !!activeWorklogId,
    queryFn: async () => {
      const token = localStorage.getItem("access_token") || ""
      const res = await fetch(`${apiBase}/worklogs/${activeWorklogId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        throw new Error("Failed to load worklog details")
      }
      return res.json()
    },
  })

  const payMutation = useMutation({
    mutationFn: async () => {
      const token = localStorage.getItem("access_token") || ""
      const payload = {
        period_start: periodStart,
        period_end: periodEnd,
        excluded_worklog_ids: excludedWorklogIds,
        excluded_user_ids: excludedFreelancerIds,
      }
      const res = await fetch(`${apiBase}/generate-remittances-for-all-users`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        throw new Error("Failed to generate remittances")
      }
      return res.json()
    },
    onSuccess: (data) => {
      showSuccessToast(
        `Payment batch created. ${data.processed_worklog_ids.length} worklogs paid.`,
      )
      queryClient.invalidateQueries({ queryKey: ["worklogs"] })
      setExcludedWorklogIds([])
      setExcludedFreelancerIds([])
    },
    onError: (error: Error) => {
      showErrorToast(error.message)
    },
  })

  const worklogs: any[] = listData?.data || []
  const freelancers = useMemo(() => {
    const grouped: Record<string, any> = {}
    for (const w of worklogs) {
      grouped[w.owner_id] = {
        owner_id: w.owner_id,
        freelancer_name: w.freelancer_name,
        freelancer_email: w.freelancer_email,
      }
    }
    return Object.values(grouped)
  }, [worklogs])

  const includedWorklogs = useMemo(() => {
    return worklogs.filter((w) => {
      const isExcludedWorklog = excludedWorklogIds.includes(w.id)
      const isExcludedFreelancer = excludedFreelancerIds.includes(w.owner_id)
      return !isExcludedWorklog && !isExcludedFreelancer
    })
  }, [worklogs, excludedWorklogIds, excludedFreelancerIds])

  const reviewTotal = useMemo(() => {
    return includedWorklogs.reduce((acc, w) => acc + Number(w.amount || 0), 0)
  }, [includedWorklogs])

  const pagedWorklogs = useMemo(() => {
    const s = (page - 1) * pageSize
    return worklogs.slice(s, s + pageSize)
  }, [worklogs, page])
  const totalPages = Math.max(1, Math.ceil(worklogs.length / pageSize))

  const toggleExcludedWorklog = (worklogId: string) => {
    setExcludedWorklogIds((prev) =>
      prev.includes(worklogId)
        ? prev.filter((id) => id !== worklogId)
        : [...prev, worklogId],
    )
  }

  const toggleExcludedFreelancer = (userId: string) => {
    setExcludedFreelancerIds((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId],
    )
  }

  const submitPayment = () => {
    if (!periodStart || !periodEnd) {
      showErrorToast("Please select a date range before confirming payment.")
      return
    }
    payMutation.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Worklog Payment Dashboard</h1>
          <p className="text-muted-foreground">
            Review worklogs, exclude entries, and confirm remittances.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Date Range & Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Input
            aria-label="Filter start date"
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
          <Input
            aria-label="Filter end date"
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
          <Select value={remittanceStatus} onValueChange={setRemittanceStatus}>
            <SelectTrigger aria-label="Filter by remittance status">
              <SelectValue placeholder="Remittance status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All</SelectItem>
              <SelectItem value="REMITTED">Remitted</SelectItem>
              <SelectItem value="UNREMITTED">Unremitted</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Worklogs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isListLoading && <p className="text-sm text-muted-foreground">Loading worklogs...</p>}
          {isListError && (
            <p className="text-sm text-destructive">Unable to fetch worklogs. Try again.</p>
          )}
          {!isListLoading && !isListError && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="py-2 text-left">Exclude</th>
                    <th className="py-2 text-left">Task</th>
                    <th className="py-2 text-left">Freelancer</th>
                    <th className="py-2 text-left">Date</th>
                    <th className="py-2 text-left">Amount</th>
                    <th className="py-2 text-left">Status</th>
                    <th className="py-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedWorklogs.map((w) => (
                    <tr key={w.id} className="border-b">
                      <td className="py-3">
                        <Checkbox
                          aria-label={`Exclude worklog ${w.task_name}`}
                          checked={excludedWorklogIds.includes(w.id)}
                          onCheckedChange={() => toggleExcludedWorklog(w.id)}
                        />
                      </td>
                      <td className="py-3 font-medium">{w.task_name}</td>
                      <td className="py-3">{w.freelancer_name || w.freelancer_email}</td>
                      <td className="py-3">{w.work_date}</td>
                      <td className="py-3">${Number(w.amount || 0).toFixed(2)}</td>
                      <td className="py-3">
                        <Badge variant={w.remittance_status === "REMITTED" ? "default" : "outline"}>
                          {w.remittance_status}
                        </Badge>
                      </td>
                      <td className="py-3 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setActiveWorklogId(w.id)}
                        >
                          <Eye className="mr-2 size-4" />
                          View entries
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Exclude Freelancers</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-2">
          {freelancers.length === 0 && (
            <p className="text-sm text-muted-foreground">No freelancers available.</p>
          )}
          {freelancers.map((f) => (
            <label
              key={f.owner_id}
              className="flex items-center gap-3 rounded border p-3 text-sm"
            >
              <Checkbox
                aria-label={`Exclude freelancer ${f.freelancer_email}`}
                checked={excludedFreelancerIds.includes(f.owner_id)}
                onCheckedChange={() => toggleExcludedFreelancer(f.owner_id)}
              />
              <span>{f.freelancer_name || f.freelancer_email}</span>
            </label>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Payment Review</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span>Selected worklogs</span>
            <span className="font-medium">{includedWorklogs.length}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span>Total payable amount</span>
            <span className="font-medium">${reviewTotal.toFixed(2)}</span>
          </div>
          <LoadingButton
            className="w-full"
            loading={payMutation.isPending}
            onClick={submitPayment}
          >
            <Wallet className="mr-2 size-4" />
            Confirm Payment Batch
          </LoadingButton>
        </CardContent>
      </Card>

      <Dialog open={!!activeWorklogId} onOpenChange={() => setActiveWorklogId(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Worklog Time Entries</DialogTitle>
            <DialogDescription>
              Review all individual time segments before payment.
            </DialogDescription>
          </DialogHeader>
          {isDetailLoading && <p className="text-sm text-muted-foreground">Loading details...</p>}
          {isDetailError && (
            <p className="text-sm text-destructive">Unable to load entry details.</p>
          )}
          {!isDetailLoading && !isDetailError && detailData && (
            <div className="space-y-3">
              {detailData.entries.map((entry: any) => (
                <div key={entry.id} className="rounded border p-3">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{entry.description || "No description"}</p>
                    <p>${Number(entry.amount || 0).toFixed(2)}</p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {entry.hours}h x ${Number(entry.hourly_rate || 0).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
