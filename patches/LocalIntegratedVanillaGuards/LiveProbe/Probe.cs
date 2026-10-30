using System;
using System.Reflection;
using Local.IntegratedVanillaGuards;
using UnityEngine;
using RimWorld;
using Verse;

namespace Local.IntegratedVanillaGuards.LiveProbe;

// Test-only assembly: load solely in an owned disposable profile, never the player's configuration.
[StaticConstructorOnStartup]
public static class Probe
{
    private sealed class HealthyGraphic : Graphic
    {
        public int Calls;
        public override Material MatSingle { get { Calls++; return BaseContent.BadMat; } }
    }

    static Probe()
    {
        LongEventHandler.ExecuteWhenFinished(Run);
    }

    private static void Run()
    {
        try
        {
            var field = typeof(Graphic_Appearances).GetField("subGraphics", BindingFlags.Instance | BindingFlags.NonPublic);
            var broken = new Graphic_Appearances { path = "RimDiag_Owned_Test_Fixture_Only" };
            field.SetValue(broken, Array.Empty<Graphic>());
            if (broken.MatSingle == null || !ReferenceEquals(broken.MatSingle, BaseContent.BadMat))
                throw new Exception("Missing default did not return the actual engine error material.");
            var child = new HealthyGraphic();
            var children = new Graphic[StuffAppearanceDefOf.Smooth.index + 1];
            children[StuffAppearanceDefOf.Smooth.index] = child;
            var healthy = new Graphic_Appearances();
            field.SetValue(healthy, children);
            if (!ReferenceEquals(healthy.MatSingle, BaseContent.BadMat) || child.Calls != 1)
                throw new Exception("Healthy original getter did not reach its child exactly once.");
            Log.Message("[IntegratedVanillaGuards.LiveProbe] PASS: actual missing-default getter returns engine BadMat; healthy getter executes original child exactly once. No Defs or saves changed.");
        }
        catch (Exception error)
        {
            Log.Error("[IntegratedVanillaGuards.LiveProbe] FAIL: " + error);
        }
    }
}
