import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Box, Typography, Button, Card, CardContent, Grid, Chip,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, MenuItem
} from '@mui/material';
import { ArrowBack, Add } from '@mui/icons-material';
import { format } from 'date-fns';

function DetectorDetail() {
  const { id } = useParams();
  const [detector, setDetector] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [openSessionDialog, setOpenSessionDialog] = useState(false);
  const [sessionForm, setSessionForm] = useState({
    run_type: '', exposure_hours: '', energy_threshold_kev: '1.0', notes: ''
  });

  useEffect(() => {
    fetch(`/api/detectors/${id}`)
      .then(res => res.json())
      .then(data => {
        setDetector(data);
        setSessions(data.sessions || []);
      })
      .catch(err => console.error('Failed to fetch detector:', err));
  }, [id]);

  const handleCreateSession = async (e) => {
    e.preventDefault();
    const response = await fetch(`/api/detectors/${id}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...sessionForm,
        exposure_hours: parseFloat(sessionForm.exposure_hours) || null,
        energy_threshold_kev: parseFloat(sessionForm.energy_threshold_kev)
      }),
    });
    const data = await response.json();
    if (data.id) {
      setSessions([...sessions, { ...sessionForm, id: data.id, session_date: new Date().toISOString() }]);
      setOpenSessionDialog(false);
    }
  };

  const runTypes = [
    { value: '本底测量', label: '本底测量' },
    { value: '能量刻度', label: '能量刻度' },
    { value: '暗物质搜索', label: '暗物质搜索' },
    { value: '校准运行', label: '校准运行' },
  ];

  if (!detector) {
    return <Typography>加载中...</Typography>;
  }

  return (
    <Box>
      <Button component={Link} to="/detectors" startIcon={<ArrowBack />} sx={{ mb: 2 }}>返回列表</Button>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h4" gutterBottom>{detector.name}</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="textSecondary">模块编号</Typography>
              <Typography variant="body1">{detector.module_code || '-'}</Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="textSecondary">靶物质</Typography>
              <Typography variant="body1">{detector.target_material || '-'}</Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="textSecondary">位置</Typography>
              <Typography variant="body1">{detector.location || '-'}</Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="body2" color="textSecondary">状态</Typography>
              <Typography variant="body1">{detector.status || '-'}</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">运行记录</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setOpenSessionDialog(true)}>
          新建运行
        </Button>
      </Box>

      <Grid container spacing={3}>
        {sessions.map((session) => (
          <Grid item xs={12} md={6} lg={4} key={session.id}>
            <Card>
              <CardContent>
                <Typography variant="h6">{session.run_type || '未命名运行'}</Typography>
                <Typography variant="body2" color="textSecondary">
                  {session.session_date && format(new Date(session.session_date), 'yyyy-MM-dd HH:mm')}
                </Typography>
                <Typography variant="body2">曝光量: {session.exposure_hours} h</Typography>
                <Typography variant="body2">阈值: {session.energy_threshold_kev} keV</Typography>
                <Box sx={{ mt: 2 }}>
                  <Chip size="small" label={session.has_recording ? '有录音' : '无录音'} sx={{ mr: 1 }} />
                  <Chip size="small" color={session.has_summary ? 'success' : 'default'}
                    label={session.has_summary ? '已生成纪要' : '未生成纪要'} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={openSessionDialog} onClose={() => setOpenSessionDialog(false)}>
        <form onSubmit={handleCreateSession}>
          <DialogTitle>新建运行会话</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2, minWidth: 320 }}>
              <TextField select label="运行类型" value={sessionForm.run_type}
                onChange={(e) => setSessionForm({ ...sessionForm, run_type: e.target.value })}>
                {runTypes.map((t) => <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>)}
              </TextField>
              <TextField label="曝光量 (小时)" type="number" value={sessionForm.exposure_hours}
                onChange={(e) => setSessionForm({ ...sessionForm, exposure_hours: e.target.value })} />
              <TextField label="能量阈值 (keV)" type="number" value={sessionForm.energy_threshold_kev}
                onChange={(e) => setSessionForm({ ...sessionForm, energy_threshold_kev: e.target.value })} />
              <TextField label="备注" multiline rows={3} value={sessionForm.notes}
                onChange={(e) => setSessionForm({ ...sessionForm, notes: e.target.value })} />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenSessionDialog(false)}>取消</Button>
            <Button type="submit" variant="contained">创建</Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
}

export default DetectorDetail;
