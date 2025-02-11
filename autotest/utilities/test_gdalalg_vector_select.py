#!/usr/bin/env pytest
# -*- coding: utf-8 -*-
###############################################################################
# Project:  GDAL/OGR Test Suite
# Purpose:  'gdal vector select' testing
# Author:   Even Rouault <even dot rouault @ spatialys.com>
#
###############################################################################
# Copyright (c) 2025, Even Rouault <even dot rouault at spatialys.com>
#
# SPDX-License-Identifier: MIT
###############################################################################

import gdaltest
import pytest

from osgeo import gdal, ogr


def get_select_alg():
    return gdal.GetGlobalAlgorithmRegistry()["vector"]["select"]


def test_gdalalg_vector_select_fields():

    select_alg = get_select_alg()
    assert select_alg.ParseCommandLineArguments(
        [
            "--fields=EAS_ID,_ogr_geometry_",
            "--of=stream",
            "../ogr/data/poly.shp",
            "streamed_output",
        ]
    )
    assert select_alg.Run()

    ds = select_alg.GetArg("output").Get().GetDataset()

    lyr = ds.GetLayer(0)
    assert lyr.GetLayerDefn().GetFieldCount() == 1
    assert lyr.GetLayerDefn().GetGeomFieldCount() == 1
    assert lyr.GetFeatureCount() == 10
    f = lyr.GetNextFeature()
    assert f["EAS_ID"] == 168
    assert f.GetGeometryRef() is not None
    lyr.ResetReading()
    assert len([f for f in lyr]) == 10
    f = lyr.GetFeature(0)
    assert f["EAS_ID"] == 168
    with pytest.raises(Exception):
        lyr.GetFeature(10)
    assert lyr.TestCapability(ogr.OLCFastFeatureCount) == 1
    assert lyr.TestCapability(ogr.OLCRandomWrite) == 0
    assert lyr.GetExtent() == (478315.53125, 481645.3125, 4762880.5, 4765610.5)
    assert lyr.GetExtent(0) == (478315.53125, 481645.3125, 4762880.5, 4765610.5)

    # Test attribute select on result layer
    lyr.SetAttributeFilter("EAS_ID = 170")
    lyr.ResetReading()
    f = lyr.GetNextFeature()
    assert f["EAS_ID"] == 170
    assert lyr.GetNextFeature() is None
    assert lyr.TestCapability(ogr.OLCFastFeatureCount) == 0
    assert lyr.GetFeatureCount() == 1
    lyr.SetAttributeFilter(None)

    # Test spatial select on result layer
    lyr.SetSpatialFilterRect(-1, -1, -1, -1)
    lyr.ResetReading()
    assert lyr.GetNextFeature() is None
    assert lyr.TestCapability(ogr.OLCFastFeatureCount) == 0
    assert lyr.GetFeatureCount() == 0
    lyr.SetSpatialFilter(None)


def test_gdalalg_vector_select_fields_geom_named(tmp_vsimem):

    src_ds = gdal.GetDriverByName("Memory").Create("", 0, 0, 0, gdal.GDT_Unknown)
    src_lyr = src_ds.CreateLayer("test", geom_type=ogr.wkbNone, srs=None)
    src_lyr.CreateGeomField(ogr.GeomFieldDefn("geom_field"))
    src_lyr.CreateGeomField(ogr.GeomFieldDefn("geom_field2"))
    out_filename = str(tmp_vsimem / "out.shp")

    select_alg = get_select_alg()
    select_alg["input"] = src_ds
    select_alg["output"] = out_filename
    select_alg["fields"] = ["geom_field2"]
    assert select_alg.ParseCommandLineArguments(["--of", "Memory"])
    assert select_alg.Run()

    ds = select_alg["output"].GetDataset()
    lyr = ds.GetLayer(0)
    assert lyr.GetLayerDefn().GetGeomFieldCount() == 1
    assert lyr.GetLayerDefn().GetGeomFieldDefn(0).GetName() == "geom_field2"


def test_gdalalg_vector_select_fields_non_existing(tmp_vsimem):

    out_filename = str(tmp_vsimem / "out.shp")

    select_alg = get_select_alg()
    with pytest.raises(
        Exception,
        match="Field 'i_do_not_exist' does not exist in layer 'poly'. You may specify --ignore-missing-fields to skip it",
    ):
        select_alg.ParseRunAndFinalize(
            ["--fields=EAS_ID,i_do_not_exist", "../ogr/data/poly.shp", out_filename]
        )


def test_gdalalg_vector_select_fields_non_existing_ignore_missing_fields(tmp_vsimem):

    out_filename = str(tmp_vsimem / "out.shp")

    select_alg = get_select_alg()
    with gdaltest.error_handler():
        assert select_alg.ParseRunAndFinalize(
            [
                "--ignore-missing-fields",
                "--fields=EAS_ID,_ogr_geometry_,i_do_not_exist",
                "../ogr/data/poly.shp",
                out_filename,
            ]
        )

    with gdal.OpenEx(out_filename) as ds:
        lyr = ds.GetLayer(0)
        assert lyr.GetLayerDefn().GetFieldCount() == 1
        assert lyr.GetLayerDefn().GetGeomFieldCount() == 1
